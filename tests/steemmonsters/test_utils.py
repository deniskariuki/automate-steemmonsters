from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import unittest
from datetime import datetime, date, timedelta
from steemmonsters.utils import (
    generate_key,
    generate_team_hash,
)


class Testcases(unittest.TestCase):
    def test_generate_key(self):
        self.assertEqual(len(generate_key(1)), 1)
        self.assertEqual(len(generate_key(5)), 5)
        self.assertEqual(len(generate_key(10)), 10)
        self.assertEqual(len(generate_key(20)), 20)

    def test_generate_team_hash(self):
        secret = "Q0KQLcrEXh"
        summoner = "C-M5EVRJO1PC"
        monsters = "C-SVOWVDHS0W", "C-RR67016F9S", "C-KO6OWLJ3QO", "C-HFJEU0FGY8", "C-HAB53TD86O"
        self.assertEqual(generate_team_hash(summoner, monsters, secret), "03d819f1ab6e1cb53764608b489746a5")
