# Fullstack Poker Coding Exercise

❗ **Don't share this exercise and solutions with others - plagiarism will cause any  existing progress of the application to be cancelled for that person who used external people and to those who shared the solution** ❗

⚠️
Use of LLMs (like ChatGPT) to code is allowed and encouraged. This exercise and its scope depends on you being proficient user of such tools to complete it in a timely manner. However, please be critical of the suggestions provided by the LLMs - you are the one responsible of producing a working and well-crafted solution that satisfies acceptance criteria. You **must** also fully understand the code you are writing.
⚠️

We aim to develop a website to play a simplified poker game. If you are not familiar with Poker, 
check the rules [here](https://bicyclecards.com/how-to-play/texas-holdem-poker) and play some hands [here](https://zone.msn.com/gameplayer/gameplayerHTML.aspx?game=texasholdem).
**Ensure** that you have a decent understanding of how the Texas Holdem poker is played.

We won't be focusing on any visual aspects of poker and UI but we will implement a simple frontend and backend engines to ensure
we can track state of a poker game hand. 

A user should be able to play a full hand from start to finish in a 6-player Texas Holdem game.

On this website, users should be able to:

- Simulate a simple hand by pressing action buttons
- All actions are logged in the text field (left side of the screen)
- Once the hand is completed, it's saved in a database and appears on the hand log (right side of the screen)

For this task, you're required to craft both a frontend (using NextJS) and a backend (with Python + FastAPI).

Game rules for this task:
 - There is Smallblind and Bigblind
 - Bigblind size is 40 chips
 - No ante
 - 6-players (6max)
 - Standard Texas Holdem with four rounds: preflop, flop, turn, river

It's a comprehensive coding exercise that will show your abilities to:
 - model problem domain correctly
 - structure code clearly
 - read and understand external code libraries
 - attention to detail and end-to-end problem solving

## Project Structure

All code should reside within a single GIT repository. 
Structure the repository to separate frontend and backend codes clearly. 
After completing the task, package the entire repository, excluding build files 
(like _node_modules_ or virtual Python environments), and share it.

## Frontend with NextJS

Develop the website using [NextJS](https://nextjs.org/docs) with 
React and TypeScript. For styling and layout, you **must** use [shadcn/ui](https://ui.shadcn.com/).

Regarding the layout and functionality, refer to the wireframes below:

![poker website coding exercise](https://gist.github.com/assets/247218/80f9332a-123b-4834-8cf5-fcd9f3f8bcb1)

### Setup
![image](https://gist.github.com/assets/247218/dc6416f6-b9d3-4982-8d82-a757d63f606c)

These controls allow to set stacks of the players all at once. "Reset" button clears the current state and starts the hand from scratch.
Once Reset is clicked, players are dealt hands. 

By default "Reset" button is called "Start". Name is changed after the first action is taken.

### Actions
![image](https://gist.github.com/assets/247218/9592220e-5311-46cb-b86e-76d8a999b5ca)

These controls allow you to interact with the current state of the hand. A user will take actions for all players.

The usual actions are available:
 - Fold
 - Check
 - Call
 - Bet
 - Raise
 - Allin

Invalid actions (like Calling when there is no Bet) should be disabled.

![image](https://gist.github.com/assets/247218/3136d969-88a0-4cfb-b057-200d967a248b)

Minus and Plus signs increase the amount for the Bet or Raise. The increments/decrements should be made
in Big Blind Size intervals (**Big Blind Size in this program is set to 40**).


### Play log

![image](https://gist.github.com/assets/247218/f0ecb0c2-6a0d-4a73-b063-c7c0717149ae)

In this area the program should capture all the actions taken. Ensure you follow the proposed format for logging (action, amounts, player names).

### Hand History

![image](https://gist.github.com/assets/247218/39235392-a2e5-4fd5-b2d9-0503d04743e8)


This section will show logs of all the hands played.

Once the hand completes, it should be saved automatically to the database.

 - The first line should show hand's UUID.
 - The second line shows stack setting + which players were Dealer, Small blind, and Big Blind
 - The third line shows what cards have the players received
 - The fourth line is the action sequence in a short format
 - The last (fifth) line should show winnings - how much each player won (+) or lost (-)

Short action sequence format:
 - Fold -> f
 - Check -> x
 - Call -> c
 - Bet AMOUNT -> bAMOUNT
 - Raise AMOUNT -> rAMOUNT
 - Allin -> allin
 - Flop, Turn, River cards -> CARD_STRING

### Notes

 - Authentication & authorization are not required for this exercise.
 - You can use design of your UI design system library of choice - it doesn't have to be exact as in the pictures but the layout has to remain similar.

**Acceptance criteria**:

- Users can play hands to completion.
- Hands are saved in the database and loaded after completion
- Hand history is shown by fetching from the backend via a RESTful API.
- The RESTful API should align with principles detailed [here](https://dev.tasubo.com/2021/08/quick-practical-introduction-to-restful-apis-and-interfaces.html).
- Incorporate at least one integration or end-to-end test for frontend functionality.
- Codebase uses React, NextJS, and TypeScript.
- It's a single page app.
- Game logic is implemented on client-side and matches validation on server-side
- There are tests for game logic
- Game logic is separated from UI logic

## Backend using Python and FastAPI

Utilize [FastAPI](https://fastapi.tiangolo.com/) with Python for the backend. Create a **repository pattern** to store data **with raw-SQL** (do not use SQLAlchemy or other frameworks) Don't worry about any SQL injections. 

You're must use PostgreSQL database. Ensure that the storage revolves around classes decorated with the [@dataclass](https://docs.python.org/3/library/dataclasses.html) annotation.

For a better understanding of the repository pattern, refer [here](https://dev.tasubo.com/2022/07/crash-course-domain-driven-design.html#repository).

Use [Poetry](https://python-poetry.org/docs/) for package management and follow [this project structure](https://github.com/martynas-subonis/py-manage/tree/main/standard). 

### Poker winnings calculations

Once you receive the game hand data from the client, you will need to perform calculations which player won and lost and how much.
This should take into account their cards and board cards. For this use library [pokerkit](https://github.com/uoftcprg/pokerkit).

Here is some example code:
```
from pokerkit import Automation, NoLimitTexasHoldem

state = NoLimitTexasHoldem.create_state(
    # Automations
    (
        Automation.ANTE_POSTING,
        Automation.BET_COLLECTION,
        Automation.BLIND_OR_STRADDLE_POSTING,
        Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
        Automation.HAND_KILLING,
        Automation.CHIPS_PUSHING,
        Automation.CHIPS_PULLING,
    ),
    True,  # Uniform antes?
    500,  # Antes
    (1000, 2000),  # Blinds or straddles
    2000,  # Min-bet
    (1125600, 553500, 553500),  # Starting stacks
    3,  # Number of players
)

state.deal_hole('Ac2d')  # Ivey
state.deal_hole('4cTh')  # Antonius
state.deal_hole('7h6h')  # Dwan

state.complete_bet_or_raise_to(7000)  # Dwan
state.complete_bet_or_raise_to(23000)  # Ivey

state.fold()  # Antonius
state.check_or_call()  # Dwan

state.burn_card()
state.deal_board('5c6c7c')  # Flop

state.complete_bet_or_raise_to(7000)
state.check_or_call() 

state.burn_card()
state.deal_board('8d')  # Turn

state.check_or_call() 
state.check_or_call() 


state.burn_card()
state.deal_board('Ts')  # River

state.check_or_call() 
state.check_or_call() 

print(state.stacks)
print(state.payoffs)
print(state.status)
```

Refer to the documentation for more examples and explanations.

**Acceptance criteria**:

- Implement the GET, POST for the hand resource.
- Resources should interact with the database via the Repository-like class.
- Entities use @dataclass annotation.
- There is at least one API test.
- Ensure the code complies with [PEP8](https://peps.python.org/pep-0008/) standards.
- Repository pattern is used for data storage and retrieval (see [here](https://dev.tasubo.com/2022/07/crash-course-domain-driven-design.html)).
- Winloss is calculated correctly

## Deployment

Draft a [Docker compose](https://docs.docker.com/compose/) file to initiate the entire stack. Upon executing:

`docker compose up -d`

and subsequently:

`start http://localhost:3000`

The website should be accessible and fully functional.

**It's crucial to verify that Docker Compose functions correctly**, enabling us to seamlessly run and test the application. **Put the docker-compose.yml file at the root of the repo.**

There should be no need to make any configuration for the tester. Ensure that the system is fully ready after `docker compose up -d` is executed.

## Evaluation criteria

When evaluating the exercise, we will take the following thins in consideration:
 - Is the code clear and simple to understand?
 - Is the poker logic implemented correctly?
 - Did you complete all the acceptance criteria mentioned?
 - Does the app work? Is it easy to run? (submitting non-working app is very bad)
 - The implementation of REST & Repository patterns is correct
 - You can answer all the questions about your work
 
❗ If the solution doesn't work after starting it with `docker compose up` **from the root directory**, it is an automatic failure so please be sure to test if this works.
