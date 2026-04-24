import bcrypt

password = "Leopoldina2026!"
hashed = "$2b$12$e573r1YKlC9UJcInjWju9u7YAoQ9EZBC2J7B1xvCQGr1qmHdsW2CW"

result = bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
print(f"Match: {result}")
