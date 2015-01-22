# Copyright (C) 2013  Hannes Bretschneider

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from hebel.layers import HiddenLayer
from hebel.pycuda_ops.elementwise import sample_dropout_mask, \
     apply_dropout_mask
from hebel.pycuda_ops import cudnn


class MaxPoolingLayer(HiddenLayer):
    n_parameters = 0
    lr_multiplier = []
    pooling_mode = 'max'

    def __init__(self, n_in, pool_size, n_filters, dropout=False,
                 l1_penalty_weight=0., l2_penalty_weight=0.):

        self.n_in = n_in
        self.pool_size = pool_size if pool_size != 'global' else n_in
        self.n_filters = n_filters

        self.l1_penalty_weight = 0.
        self.l2_penalty_weight = 0.

        self.dropout = dropout

        self.n_units_per_filter = self._compute_n_units(self.n_in, self.pool_size, self.n_filters)
        self.n_units = self.n_units_per_filter * self.n_filters

    @staticmethod
    def _compute_n_units(n_in, pool_size, n_filters):
        """ Compute the number of output units """
        if pool_size is None:
            pool_size = 1
        return n_in // pool_size

    @property
    def parameters(self):
        return []

    @parameters.setter
    def parameters(self, value):
        pass

    def update_parameters(self, values, stream=None):
        pass

    @property
    def l1_penalty(self):
        return 0.

    @property
    def l2_penalty(self):
        return 0.

    def feed_forward(self, input_data, prediction=False):
        pooling_desc = cudnn.PoolingDesc(1, self.pool_size, mode=self.pooling_mode)

        if self.pool_size > 1:
            pooled = cudnn.pooling_forward(pooling_desc, input_data)
        else:
            pooled = input_data

        if self.dropout and prediction:
            pooled *= .5

        if self.dropout and not prediction:
            dropout_mask = sample_dropout_mask(pooled)
            return pooled, pooling_desc, dropout_mask

        return pooled, pooling_desc

    def backprop(self, input, df_output, cache=None):
        if cache is None:
            cache = self.feed_forward(input)

        if len(cache) == 2:
            activations, pooling_desc = cache
        elif len(cache) == 3:
            activations, pooling_desc, dropout_mask = cache
        else:
            raise ValueError

        if self.dropout and dropout_mask is not None:
            apply_dropout_mask(df_output, dropout_mask)

        if self.pool_size > 1:
            df_input = cudnn.pooling_backward(pooling_desc, input,
                                              activations, df_output)
        else:
            df_input = df_output
        return tuple(), df_input

class AveragePoolingLayer(MaxPoolingLayer):
    pooling_mode = 'avg'