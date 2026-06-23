from database import save_user


class MockUser:

    def __init__(self):
        self.id = 999999
        self.username = "sourabh_test"
        self.first_name = "Sourabh"


user = MockUser()

result = save_user(user)

print(result)