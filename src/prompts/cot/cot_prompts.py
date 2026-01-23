"""
CoT (Chain-of-Thought) 策略的提示词模块
"""

from typing import Optional

def get_cot_prompt(problem: str, language: str, dataset_type: str = "HumanEval") -> str:
    """
    获取 CoT 提示词
    
    Args:
        problem: 问题描述
        language: 编程语言
        dataset_type: 数据集类型 (HumanEval, APPS, XCodeEval, CodeContest)
        
    Returns:
        完整的 CoT 提示词
    """
    # 根据数据集类型选择 few-shot examples
    if dataset_type == "HumanEval":
        few_shot = HUMANEVAL_EXAMPLES
    elif dataset_type == "APPS":
        few_shot = APPS_EXAMPLES
    elif dataset_type == "XCodeEval":
        few_shot = XCODE_EXAMPLES
    elif dataset_type == "CodeContest":
        few_shot = CODECONTEST_EXAMPLES
    else:
        few_shot = HUMANEVAL_EXAMPLES  # 默认使用 HumanEval
    
    return f"""{few_shot}

-------

{problem}

## Let's think step by step and generate {language} code to solve the problem.
# ----------------
Important: Your response must contain only the {language} code to solve this problem inside ``` block."""


# HumanEval Few-shot Examples
HUMANEVAL_EXAMPLES = """
def encrypt(s):
    '''
    Create a function encrypt that takes a string as an argument and
    returns a string encrypted with the alphabet being rotated. 
    The alphabet should be rotated in a manner such that the letters 
    shift down by two multiplied to two places.
    For example:
    encrypt('hi') returns 'lm'
    encrypt('asdfghjkl') returns 'ewhjklnop'
    encrypt('gf') returns 'kj'
    encrypt('et') returns 'ix'
    '''
    # Let's think step by step.

    # Define the alphabet as a string
    d = 'abcdefghijklmnopqrstuvwxyz'
    
    # Initialize an empty string to store the encrypted result
    out = ''
    
    # Iterate through each character in the input string
    for c in s:
        # Check if the character is a letter in the alphabet
        if c in d:
            # Find the index of the current letter in the alphabet
            index = d.index(c)
            
            # Rotate the alphabet by two multiplied to two places
            # Use modulo 26 to handle wrapping around the alphabet
            rotated_index = (index + 2 * 2) % 26
            
            # Append the encrypted letter to the result string
            out += d[rotated_index]
        else:
            # If the character is not a letter, append it unchanged to the result string
            out += c
    
    # Return the final encrypted string
    return out


-------

def check_if_last_char_is_a_letter(txt):
    ''' 
    Create a function that returns True if the last character of a given string is an alphabetical character and is not a part of a word, and False otherwise. Note: 'word' is a group of characters separated by space.
    Examples:
    check_if_last_char_is_a_letter('apple pie') → False
    check_if_last_char_is_a_letter('apple pi e') → True
    check_if_last_char_is_a_letter('apple pi e ') → False
    check_if_last_char_is_a_letter('') → False
    '''    
    # Let's think step by step.

    # Split the input string by space to get a list of words
    words = txt.split(' ')
    
    # Extract the last word from the list
    last_word = words[-1]
    
    # Check if the last character of the last word is an alphabetical character
    # and is not part of a longer word (length of last word is 1)
    is_last_char_letter = len(last_word) == 1 and (97 <= ord(last_word.lower()) <= 122)
    
    # Return True if the conditions are met, False otherwise
    return is_last_char_letter

-------

def file_name_check(file_name):
    '''
    Create a function which takes a string representing a file's name, and returns 'Yes' if the the file's name is valid, and returns 'No' otherwise. A file's name is considered to be valid if and only if all the following conditions are met: - There should not be more than three digits ('0'-'9') in the file's name. - The file's name contains exactly one dot '.' - The substring before the dot should not be empty, and it starts with a letter from the latin alphapet ('a'-'z' and 'A'-'Z'). - The substring after the dot should be one of these: ['txt', 'exe', 'dll']
    Examples:
    file_name_check('example.txt') => 'Yes'
    file_name_check('1example.dll') => 'No' (the name should start with a latin alphapet letter)
    '''    
    # Let's think step by step.

    # Define a list of valid file extensions
    valid_suffixes = ['txt', 'exe', 'dll']
    
    # Split the file name into two parts using the dot as a separator
    parts = file_name.split(sep='.')
    
    # Check if there are exactly two parts after splitting
    if len(parts) != 2:
        return 'No'
    
    # Check if the second part (suffix) is in the list of valid suffixes
    if not parts[1] in valid_suffixes:
        return 'No'
    
    # Check if the first part (prefix) is not empty and starts with a letter from the Latin alphabet
    if len(parts[0]) == 0 or not parts[0][0].isalpha():
        return 'No'
    
    # Count the number of digits in the prefix and check if it's not more than three
    num_digits = len([x for x in parts[0] if x.isdigit()])
    if num_digits > 3:
        return 'No'
    
    # If all conditions are met, return 'Yes', indicating a valid file name
    return 'Yes'

-------

def fruit_distribution(s,n):
    '''
    In this task, you will be given a string that represents a number of apples and oranges that are distributed in a basket of fruit this basket contains apples, oranges, and mango fruits. Given the string that represents the total number of the oranges and apples and an integer that represent the total number of the fruits in the basket return the number of the mango fruits in the basket.
    for examble:
    fruit_distribution('5 apples and 6 oranges', 19) = 19 - 5 - 6 = 8
    fruit_distribution('0 apples and 1 oranges',3) = 3 - 0 - 1 = 2
    fruit_distribution('2 apples and 3 oranges', 100) = 100 - 2 - 3 = 95
    fruit_distribution('100 apples and 1 oranges',120) = 120 - 100 - 1 = 19
    '''
    # Let's think step by step.
    
    # Initialize an empty list to store the numeric values (apples and oranges) extracted from the string
    lis = list()

    # Split the input string by space and iterate through each word
    for i in s.split(' '):
        # Check if the word is a numeric value (digit)
        if i.isdigit():
            # Convert the numeric value to an integer and append it to the list
            lis.append(int(i))

    # Calculate the number of mango fruits by subtracting the sum of apples and oranges from the total
    return n - sum(lis)

-------

def prime_fib(n: int):
    '''
    prime_fib returns n-th number that is a Fibonacci number and it's also prime.
    Examples:
    >>> prime_fib(1) 2
    >>> prime_fib(2) 3
    >>> prime_fib(3) 5
    >>> prime_fib(4) 13
    >>> prime_fib(5) 89
    '''
    # Let's think step by step.

    # Import the math module for the square root function
    import math
    
    # Define a helper function to check if a number is prime
    def is_prime(p):
        if p < 2:
            return False
        for k in range(2, min(int(math.sqrt(p)) + 1, p - 1)):
            if p % k == 0:
                return False
        return True

    # Initialize the Fibonacci sequence with the first two numbers
    f = [0, 1]
    
    # Continue generating Fibonacci numbers until finding the n-th prime Fibonacci number
    while True:
        f.append(f[-1] + f[-2])
        
        # Check if the latest Fibonacci number is prime
        if is_prime(f[-1]):
            n -= 1
        
        # If the desired n-th prime Fibonacci number is found, return it
        if n == 0:
            return f[-1]
"""

# APPS Few-shot Examples (简化版，完整版在 CoT.py 第 197-418 行)
APPS_EXAMPLES = """
An accordion is a string (yes, in the real world accordions are musical instruments, but let's forget about it for a while) which can be represented as a concatenation of: an opening bracket (ASCII code $091$), a colon (ASCII code $058$), some (possibly zero) vertical line characters (ASCII code $124$), another colon, and a closing bracket (ASCII code $093$). The length of the accordion is the number of characters in it.

For example, [::], [:||:] and [:|||:] are accordions having length $4$, $6$ and $7$. (:|:), {:||:}, [:], ]:||:[ are not accordions. 

You are given a string $s$. You want to transform it into an accordion by removing some (possibly zero) characters from it. Note that you may not insert new characters or reorder existing ones. Is it possible to obtain an accordion by removing characters from $s$, and if so, what is the maximum possible length of the result?


-----Input-----

The only line contains one string $s$ ($1 \\le |s| \\le 500000$). It consists of lowercase Latin letters and characters [, ], : and |.


-----Output-----

If it is not possible to obtain an accordion by removing some characters from $s$, print $-1$. Otherwise print maximum possible length of the resulting accordion.


-----Examples-----
Input
|[a:b:|]

Output
4

Input
|]:[|:]

Output
-1

2
1 2

## Let's think step by step and generate code to solve the problem.

```python
# Take user input and assign it to the variable 's'
s = input()

# Calculate the length of the string 's' and assign it to the variable 'n'
n = len(s)

# Initialize variables to store the indices of '[' and ']'
ind = -1
bind = -1

# Variable to track whether '[' or ']' characters have been encountered
f = False

# Step 1: Find the index of the first '[' character after encountering ':'
for i in range(n):
    if s[i] == '[':
        f = True
    elif s[i] == ':':
        if f:
            ind = i
            break

# Reset the flag variable
f = False

# Step 2: Find the index of the last ']' character before encountering ':'
for i in range(n - 1, -1, -1):
    if s[i] == ']':
        f = True
    elif s[i] == ':':
        if f:
            bind = i
            break

# Check conditions to determine if it's possible to obtain an accordion
if ind == -1 or bind == -1:
    # Print -1 if '[' or ']' characters were not found
    print(-1)
elif ind >= bind:
    # Print -1 if the order of '[' and ']' characters is incorrect
    print(-1)
else:
    # Initialize the length of the accordion to 4 (opening and closing brackets, and two colons)
    ans = 4
    # Step 3: Count the number of '|' characters between '[' and ']' indices (inclusive)
    for i in range(ind + 1, bind):
        if s[i] == '|':
            ans += 1
    # Print the calculated length of the resulting accordion
    print(ans)
```
"""

# XCode Few-shot Examples (简化版)
XCODE_EXAMPLES = """
Problem Description:
The Hat is a game of speedy explanation/guessing words (similar to Alias). It's fun. Try it! In this problem, we are talking about a variant of the game when the players are sitting at the table and everyone plays individually (i.e. not teams, but individual gamers play).$$$n$$$ people gathered in a room with $$$m$$$ tables ($$$n \\ge 2m$$$). They want to play the Hat $$$k$$$ times. Thus, $$$k$$$ games will be played at each table. Each player will play in $$$k$$$ games.To do this, they are distributed among the tables for each game. During each game, one player plays at exactly one table. A player can play at different tables.Players want to have the most "fair" schedule of games. For this reason, they are looking for a schedule (table distribution for each game) such that:  At any table in each game there are either $$$\\lfloor\\frac{n}{m}\\rfloor$$$ people or $$$\\lceil\\frac{n}{m}\\rceil$$$ people (that is, either $$$n/m$$$ rounded down, or $$$n/m$$$ rounded up). Different numbers of people can play different games at the same table. Let's calculate for each player the value $$$b_i$$$ — the number of times the $$$i$$$-th player played at a table with $$$\\lceil\\frac{n}{m}\\rceil$$$ persons ($$$n/m$$$ rounded up). Any two values of $$$b_i$$$must differ by no more than $$$1$$$. In other words, for any two players $$$i$$$ and $$$j$$$, it must be true $$$|b_i - b_j| \\le 1$$$.

Sample Inputs: ['3\\n5 2 2\\n8 3 1\\n2 1 3']
Sample Outputs: ['3 1 2 3\\n2 4 5\\n3 4 5 2\\n2 1 3\\n\\n2 6 2\\n3 3 5 1\\n3 4 7 8\\n\\n2 2 1\\n2 2 1\\n2 2 1']

## Let's think step by step and generate code to solve the problem.

```python
# Read the number of test cases
t = int(input())

# Iterate over each test case
for _ in range(t):
    # Read n, m, and k for the current test case
    n, m, k = map(int, input().split())
    
    # Initialize a list to store groups of players for each game
    groups = []
    
    # Initialize an array containing player indices
    arr = [(i + 1) for i in range(n)]
    
    z = 0
    
    # Check if the number of players is not divisible by the number of tables
    if n % m != 0:
        # Determine the size of the larger group
        larger = (n // m) + 1
        
        # Distribute players to larger groups until the number of players is divisible by the number of tables
        while n % m != 0:
            groups.append(larger)
            n -= larger
            m -= 1
            z += larger
    
    # Calculate the size of smaller groups
    a = n // m
    
    # Create groups with the calculated sizes
    for _ in range(m):
        groups.append(a)
    
    # Iterate over each game
    while k:
        curr = 0
        
        # Print the schedule for the current game
        for i in groups:
            print(i, end=" ")
            j = i
            
            # Print player indices for the current table
            while j:
                print(arr[curr], end=" ")
                curr += 1
                j -= 1
            
            print()
        
        # Rotate the array of player indices to simulate the rotation of players
        arr = arr[z:] + arr[:z]
        k -= 1
    
    # Print a blank line to separate responses for different sets of inputs
    print()
```
"""

# CodeContest Few-shot Examples (简化版)
CODECONTEST_EXAMPLES = """
Three little pigs from all over the world are meeting for a convention! Every minute, a triple of 3 new pigs arrives on the convention floor. After the n-th minute, the convention ends.

The big bad wolf has learned about this convention, and he has an attack plan. At some minute in the convention, he will arrive and eat exactly x pigs. Then he will get away.

The wolf wants Gregor to help him figure out the number of possible attack plans that involve eating exactly x pigs for various values of x (1 ≤ x ≤ 3n). Two attack plans are considered different, if they occur at different times or if the sets of little pigs to eat are different.

Note that all queries are independent, that is, the wolf does not eat the little pigs, he only makes plans!

Input

The first line of input contains two integers n and q (1 ≤ n ≤ 10^6, 1 ≤ q ≤ 2⋅ 10^5), the number of minutes the convention lasts and the number of queries the wolf asks.

Each of the next q lines contains a single integer x_i (1 ≤ x_i ≤ 3n), the number of pigs the wolf will eat in the i-th query.

Output

You should print q lines, with line i representing the number of attack plans if the wolf wants to eat x_i pigs. Since each query answer can be large, output each answer modulo 10^9+7.

Examples

Input

2 3
1
5
6

Output

9
6
1

## Let's think step by step and generate code to solve the problem.

```python
def inverses(n, P):
    inv = [1] * (n + 1)
    for i in range(2, n + 1):
        inv[i] = inv[P % i] * (P - P // i) % P
    return inv

mod = 10**9 + 7

def init():
    fac[0] = ifac[0] = 1
    inv = inverses(N, mod)
    for i in range(1, N):
        fac[i] = (fac[i - 1] * i) % mod
        ifac[i] = (ifac[i - 1] * inv[i]) % mod

def comb(n, k):
    return (fac[n] * ifac[n - k] * ifac[k]) % mod

N = 3 * 10**6 + 10

fac = [0] * N
ifac = [0] * N

init()

def main():
    n, Q = map(int, input().split())
    sz = 3 * (n + 1)

    # Create a list to store coefficients of polynomial p(x)
    p = [0] * (sz + 1)

    # Initialize coefficients of p(x) using binomial coefficients
    for i in range(1, sz + 1):
        p[i] = comb(sz, i)

    # Backward iteration to calculate coefficients of p(x-1) and p(x-2)
    for i in range(sz, 2, -1):
        p[i - 1] = ((p[i - 1] - 3 * p[i]) % mod + mod) % mod
        p[i - 2] = ((p[i - 2] - 3 * p[i]) % mod + mod) % mod

    # Remove extra elements at the beginning of p
    p = p[3:]

    # Answer queries based on calculated coefficients
    for _ in range(Q):
        x = int(input())
        print(p[x])

# Call the main function
main()
```
"""

