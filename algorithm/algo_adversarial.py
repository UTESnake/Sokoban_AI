from algorithm.common import beam_best_first, greedy_best_first


def minimax(game):
    return greedy_best_first(game)


def alpha_beta(game):
    return beam_best_first(game, beam_width=4)


def expectimax(game):
    return beam_best_first(game, beam_width=5)
