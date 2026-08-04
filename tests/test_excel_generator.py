from src.excel_generator import generate_excel

test_cases = [

    {
        "S.No": 1,
        "Title of Test Case": "Verify Login",
        "Pre Requisites": "Application should be running",
        "Actions to be done": "Enter Username and Password",
        "Expected Results": "Login Successful",
        "Test Data": "Username=test Password=Pass123",
        "Testing Technique": "Functional Testing"
    },

    {
        "S.No": 2,
        "Title of Test Case": "Verify Invalid Password",
        "Pre Requisites": "Application should be running",
        "Actions to be done": "Enter Invalid Password",
        "Expected Results": "Error Message",
        "Test Data": "Username=test Password=Wrong123",
        "Testing Technique": "Negative Testing"
    }

]

generate_excel(
    test_cases,
    "output/TestCases.xlsx"
)