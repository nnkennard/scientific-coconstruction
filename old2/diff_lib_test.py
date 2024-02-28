import unittest
import diff_lib

tokens_1 = list("aabce")
tokens_2 = list("abcd")
tokens_3 = list("bce")
tokens_4 = list("aabcd")

real_tokens_1 = "This is a sentence .".split()
real_tokens_2 = "This is another sentence !".split()


class TestDiffLib(unittest.TestCase):

    def test_overall(self):
        b = diff_lib.factored_simple_diffs(real_tokens_1,
                                           real_tokens_2,
                                           min_len=1)
        self.assertEqual(set(b.keys()), set([2, 4]))
        self.assertEqual(tuple(b[2]), (2, ('a', ), ('another', )))
        self.assertEqual(tuple(b[4]), (4, ('.', ), ('!', )))

    def test_matching_blocks_start_unmatched(self):
        blocks = diff_lib.get_matching_blocks(tokens_1, tokens_3)
        self.assertEqual(blocks, [(0, 0, 0), (2, 0, 3), (5, 3, 0)])

    def test_matching_blocks(self):
        blocks = diff_lib.get_matching_blocks(tokens_1, tokens_4)
        self.assertEqual(blocks, [(0, 0, 4), (5, 5, 0)])


unittest.main()
