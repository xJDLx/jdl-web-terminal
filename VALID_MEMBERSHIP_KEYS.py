import secrets
import string

# This generates a random 12-character code like '8Xk2Lp9QzW1m'
alphabet = string.ascii_letters + string.digits
new_key = ''.join(secrets.choice(alphabet) for i in range(12))
print(new_key)