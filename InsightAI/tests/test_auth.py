import unittest
from auth import hash_password, verify_password, valid_email

class AuthTests(unittest.TestCase):
    def test_password_hash_and_verify(self):
        encoded = hash_password("A-long-password-123!")
        self.assertNotEqual(encoded, "A-long-password-123!")
        self.assertTrue(verify_password("A-long-password-123!", encoded))
        self.assertFalse(verify_password("wrong-password", encoded))

    def test_email_validation(self):
        self.assertTrue(valid_email("student@example.com"))
        self.assertFalse(valid_email("not-an-email"))

if __name__ == "__main__":
    unittest.main()
