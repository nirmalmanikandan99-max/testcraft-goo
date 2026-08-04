from src.testcase_generator import generate_testcases

requirement = """
{
"module_name":"Login",

"input_fields":[
"Username",
"Password"
],

"business_rules":[
"Username mandatory",
"Password mandatory"
],

"workflow":[
"Enter Username",
"Enter Password",
"Click Login",
"Navigate Dashboard"
]
}
"""

techniques = """
{
"Functional Testing":true,
"Positive Testing":true,
"Negative Testing":true,
"UI Validation":true,
"Field Validation":true,
"Business Rule Validation":true
}
"""

result = generate_testcases(
    requirement,
    techniques
)

print(result)