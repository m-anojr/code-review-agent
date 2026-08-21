import os
import non_existent_module  # The linter tool should catch this

def calculate_discount(price, discount_percent):
    # Logical Bug: We are adding the discount instead of subtracting it! 
    # The LLM should easily catch this logic error.
    final_price = price + (price * discount_percent / 100)
    return final_price

def execute_user_script(user_input):
    # Security Flaw: Using eval() on raw user input.
    # The deterministic regex rules won't catch this, but the Agentic LLM should flag it as a massive vulnerability.
    result = eval(user_input)
    return result

def load_config():
    # Syntax issue: missing return statement or undefined variable usage
    config = {"timeout": 30, "retries": 3}
    print(confg)  # Typo: confg instead of config
