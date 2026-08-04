from src.json_validator import validate_json

sample_response = '''
[
    {
        "S.No": 1,
        "Title of Test Case": "Verify Login with Valid Credentials",
        "Pre Requisites": "User account exists",
        "Actions to be done": "Enter valid username and password. Click Login.",
        "Expected Results": "User should be navigated to Dashboard.",
        "Test Data": "Username: testuser | Password: Pass@123",
        "Testing Technique": "Functional Testing"
    }
]
'''

result = validate_json(sample_response)

print(result)