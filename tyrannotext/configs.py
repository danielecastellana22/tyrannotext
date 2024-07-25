from argparse import Namespace


__all__ = ['SimpleConfig']

_default_vals = {'origin_tol': 0.01,
                 'font_tol': 0.01,
                 'alignment_tol': 0.01,
                 'n_char_dist': 2,
                 'n_line_dist': 0.8,
                 'n_line_footer_margin': 5}


class SimpleConfig(Namespace):
    def __init__(self, **kwargs):
        diff = set(kwargs.keys()).difference(set(_default_vals.keys()))
        if len(diff) > 0:
            raise ValueError(f'Options {diff} are not known!')
        d = {}
        d.update(_default_vals)
        d.update(kwargs)
        super().__init__(**d)

# TODO: implement specific config for single-column, two-columns, etc..
