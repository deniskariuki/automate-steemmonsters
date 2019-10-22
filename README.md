# Python library for steem monsters!

[![Build status](https://ci.appveyor.com/api/projects/status/01t13py6r7f1aotj?svg=true)](https://ci.appveyor.com/project/holger80/steemmonsters)


Steem monsters is a fully decentralized trading card game on the steem blockchain.

## Installation
```
pip install beem termcolor colorama
```


## Commands
The steem monsters shell can be started with
```
python steemmonsters.py
```

```
sm> stream
```
This command shows the current battles and which player are participating

```
sm> play deck_name
```
`deck_name` is one of the stored decks defined in `config.json`.


```
sm> play random 
```
selects randomly a deck.

```
sm> show_deck deck_name 
```
shows deck `deck_name`.

## Setup the beem wallet
Create a new wallet, when not already done.
```
beempy createwallet
```
Add the posting key of the player by:
```
beempy addkey
```


## Configuration
```
{
    "wallet_password": "123",
    "account": "holger80",
    "match_type": "Ranked",
    "decks": {
                "death1": ["Zintar Mortalis", "Haunted Spirit", "Skeleton Assassin", "Twisted Jester", "Haunted Spider", "Screaming Banshee", "Undead Priest"],
                "water1": ["Alric Stormbringer", "Naga Warrior", "Medusa", "Mischievous Mermaid", "Pirate Captain", "Crustacean King"],
                "fire1": ["Malric Inferno", "Serpentine Soldier", "Elemental Phoenix", "Goblin Shaman", "Fire Demon"],
    },
    "play_counter": 1,
    "play_delay": 10,
    "play_inside_ranking_border": false,
    "ranking_border": [2500, 3000],
    "stop_on_loosing_streak": 2
}
```

* `wallet_password` is the `beempy` wallet password
* `account`: steem user name of the player
* `match_type`: match type
* `decks` contains the different pre defined decks. There is no mana_cap check
* `play_counter`  how often a deck is played, -1 means play foreever
* `play_delay`  delay in seconds between two rounds
* `play_inside_ranking_border`  if true, playing is stopped when outside ranking_border
* `ranking_border`  continue to play, when inside this border
* `stop_on_loosing_streak` stops playing when given loosing streak is reached