# Catch the Coins
A real-time multiplayer game built with Python and raw sockets, designed to demonstrate state synchronization under simulated high-latency conditions.

## How to Run
Install Python 3.x and Pygame: ```pip install pygame```.

Run ```python3 server.py``` in a terminal to start the authoritative host.

Run ```python3 client.py``` in two separate terminals to join the session.

Use Arrow Keys to move and R to reset the game.

## Core Features (Prompt Requirements)
Built with Python and raw TCP sockets; no middleware used.

Authoritative server manages physics, collisions, and scoring for security.


Custom middleware simulates 200ms latency to test network resilience.

Entity interpolation buffers state for smooth rendering despite 200ms lag.


Server validates all inputs to prevent spoofing and self-reported scoring.

Synchronized coin spawning and scoring managed strictly by server authority.

Server-side collision resolution ensures consistent game state across clients.

Distinct server and client components running as separate processes.

## Extra Features & Improvements
Input rate-limiting security layer prevents client-side speed hacking.

Server-side "Bounce and Stun" mechanics for physical player collisions.

Soft-reset feature (R) restarts round without killing the server.

Waiting Room UI pauses game logic until two players connect.

Multi-tiered coin system (Gold, Silver, Bronze) with different score values.

Background image support with automatic fallback to dark mode.
