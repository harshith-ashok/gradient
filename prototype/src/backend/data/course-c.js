import { q, fc, sub } from './helpers.js'

export const courseC = {
  id: 'c-cs101',
  code: 'CS 101',
  title: 'Programming in C',
  department: 'Computer Science',
  credits: 4,
  level: 'Undergraduate · Year 1',
  accent: '#8e2433',
  description:
    'A first course in programming using C. Covers the core language, functions, and the memory model that makes C powerful and unforgiving.',
  instructorId: 'u-rao',
  status: 'published',
  source: { fileName: 'CS101-syllabus.pdf' },
  topics: [
    {
      id: 'c-t1',
      title: 'Language Fundamentals',
      subtopics: [
        sub('c-vars', 'Variables and data types', 'Declaring variables, integer and floating-point types, type sizes and conversions.', {
          points: ['A variable names a typed region of memory', 'int, char, float and double have different sizes and ranges', 'Implicit conversion happens in mixed expressions', 'sizeof reports the size of a type in bytes'],
          summary: [
            'A variable is a named piece of memory with a fixed type. The type decides how many bytes it uses and how those bytes are read. Common types are char (one byte), int (usually four), float and double for real numbers.',
            'When different types meet in one expression, C converts them implicitly, usually towards the wider type. Dividing two ints discards the fraction, so 7 / 2 is 3, not 3.5. Use a cast such as (double)7 / 2 when you need the real quotient.',
          ],
          cards: [fc('What does sizeof(int) return on most modern systems?', '4 — the size of an int in bytes.'), fc('What is the result of 7 / 2 when both are int?', '3. Integer division drops the fractional part.'), fc('How do you force real-number division of two ints a and b?', 'Cast one operand: (double)a / b.')],
          questions: [
            q('What is the value of 7 / 2 in C when both operands are int?', '3', ['3.5', '4', '2'], 'Integer division truncates toward zero, so the fractional .5 is discarded.'),
            q('Which type is normally used to store a single character?', 'char', ['string', 'int[]', 'text'], 'char holds one byte and is the standard type for a single character.'),
            q('What does the sizeof operator return?', 'The size of a type or object in bytes', ['The number of elements in an array always', 'The value stored in a variable', 'The address of a variable'], 'sizeof yields the size in bytes, as a value of type size_t.'),
            q('Which expression gives 3.5 for int a = 7, b = 2?', '(double)a / b', ['a / b', 'a % b', '(int)a / b'], 'Casting one operand to double makes the division a floating-point division.'),
          ],
          remediation: {
            explanation: 'Think of each type as a different sized box. An int box holds a whole number, so when the answer has a fraction the box simply cannot hold it and the fraction is cut off. Use a double box when you need the fraction.',
            steps: ['Write 7 / 2 and 7.0 / 2 on paper and predict both results before running them.', 'Print sizeof(char), sizeof(int), sizeof(double) on your own machine.', 'Rewrite a division of two ints so it keeps the fractional part.'],
          },
        }),
        sub('c-flow', 'Operators and control flow', 'Arithmetic, relational and logical operators; if/else, switch and loops.', {
          points: ['Relational operators yield 1 (true) or 0 (false)', '&& and || short-circuit', 'for, while and do-while differ in when they test the condition', 'break leaves a loop; continue skips to the next iteration'],
          summary: [
            'C has no separate boolean in its original form: any non-zero value is true and zero is false. Relational operators such as == and < produce 1 or 0. The logical operators && and || short-circuit, so the right-hand side is only evaluated if it can still change the result.',
            'Use for when the iteration count is known, while when you loop until a condition changes, and do-while when the body must run at least once. A common bug is writing = (assignment) where == (comparison) was intended.',
          ],
          cards: [fc('What is the difference between = and ==?', '= assigns a value; == compares two values.'), fc('What does short-circuit evaluation mean for A && B?', 'If A is false, B is not evaluated at all.'), fc('Which loop always runs its body at least once?', 'do-while, because the condition is tested after the body.')],
          questions: [
            q('Which loop guarantees the body executes at least once?', 'do-while', ['while', 'for', 'None of them'], 'do-while checks its condition after running the body.'),
            q('What does if (x = 5) do?', 'Assigns 5 to x and is always true', ['Compares x with 5', 'Causes a compile error', 'Is always false'], 'A single = is assignment; the expression value is 5, which is non-zero and therefore true.'),
            q('In (a != 0 && b / a > 2), why is the division safe?', 'If a is 0 the && short-circuits and b / a is never evaluated', ['The compiler rewrites the division', 'Division by zero is defined as 0', 'It is not safe'], 'Short-circuit evaluation skips the right operand when the left operand is already false.'),
            q('What does continue do inside a loop?', 'Skips the rest of the current iteration', ['Exits the loop', 'Restarts the program', 'Exits the function'], 'continue jumps to the next iteration; break would exit the loop.'),
          ],
          remediation: {
            explanation: 'Control flow is just decisions and repetition. Trace a loop by hand with a small table: one column per variable, one row per iteration. Most mistakes (off-by-one, = vs ==) show up immediately.',
            steps: ['Trace for (i = 0; i < 3; i++) by hand and list every value of i.', 'Fix the bug in: if (n = 0) { ... } so it compares.', 'Rewrite a while loop as a for loop and back again.'],
          },
        }),
        sub('c-func', 'Functions', 'Defining functions, parameters, return values, prototypes and scope.', {
          points: ['A prototype declares a function before its use', 'Arguments are passed by value', 'Local variables live only during the call', 'A function returns at most one value'],
          summary: [
            'A function packages reusable work behind a name, a parameter list and a return type. A prototype such as int add(int a, int b); tells the compiler the shape of the function before its definition appears.',
            'C passes arguments by value: the function receives copies, so changing a parameter does not change the caller’s variable. To modify the caller’s data you pass its address (a pointer). Local variables exist only while the function runs.',
          ],
          cards: [fc('What does pass by value mean?', 'The function gets a copy of each argument; changes do not affect the caller’s variables.'), fc('What is a function prototype for?', 'It declares the name, parameters and return type before the definition so calls can be checked.'), fc('How long does a local variable live?', 'Until the function returns.')],
          questions: [
            q('In C, what happens when you modify a parameter inside a function?', 'Only the local copy changes', ['The caller’s variable changes too', 'The program crashes', 'The compiler rejects it'], 'Arguments are passed by value, so the function works on a copy.'),
            q('What is the purpose of a function prototype?', 'To declare a function before it is defined', ['To allocate memory for it', 'To make it run faster', 'To hide it from other files'], 'A prototype lets the compiler check calls made before the definition.'),
            q('Which return type is used for a function that returns nothing?', 'void', ['null', 'int', 'empty'], 'void indicates that no value is returned.'),
            q('Where is a local variable visible?', 'Only inside the block or function where it is declared', ['In every function in the file', 'In every file of the program', 'Until the program exits'], 'Block scope limits the variable to its enclosing braces.'),
          ],
          remediation: {
            explanation: 'Imagine photocopying a worksheet and handing the copy to a friend. Whatever they write on it does not change your original. That is pass by value. To let them edit your original you must hand over where it lives: its address.',
            steps: ['Write swap(int a, int b) and show that the caller’s values do not change.', 'Add a prototype above main and move the definition below it.', 'List the scope of every variable in a small program.'],
          },
        }),
      ],
    },
    {
      id: 'c-t2',
      title: 'Memory and Pointers',
      subtopics: [
        sub('c-ptr', 'Pointers', 'Addresses, the & and * operators, pointer arithmetic and passing by pointer.', {
          points: ['A pointer stores a memory address', '& gives the address of; * dereferences', 'Pointers let functions modify the caller’s data', 'A NULL or uninitialised pointer must not be dereferenced'],
          summary: [
            'A pointer is a variable that holds the address of another variable. The address-of operator & produces an address and the dereference operator * follows it to the value. If int x = 5; int *p = &x; then *p is 5, and writing *p = 9 changes x.',
            'Passing a pointer to a function lets it modify the caller’s data, which is how swap works. Dereferencing a NULL, uninitialised or dangling pointer is undefined behaviour, so always initialise pointers and check for NULL.',
          ],
          cards: [fc('What does the & operator do?', 'It yields the address of its operand.'), fc('What does *p mean when p is a pointer?', 'The value stored at the address held in p (dereferencing).'), fc('Why is dereferencing NULL dangerous?', 'It is undefined behaviour and typically crashes the program.')],
          questions: [
            q('Given int x = 5; int *p = &x; what does *p = 9; do?', 'Changes x to 9', ['Changes p to 9', 'Does nothing', 'Causes a compile error'], 'p holds x’s address, so *p refers to x itself.'),
            q('What does the & operator return?', 'The address of a variable', ['The value of a variable', 'The size of a variable', 'A copy of a variable'], '& is the address-of operator.'),
            q('Which function correctly swaps two ints for the caller?', 'void swap(int *a, int *b)', ['void swap(int a, int b)', 'int swap(int a)', 'void swap(int &a)'], 'Only pointers give the function access to the caller’s variables in C.'),
            q('What is the risk of dereferencing an uninitialised pointer?', 'Undefined behaviour, often a crash', ['It returns zero', 'It allocates memory automatically', 'Nothing, it is safe'], 'The pointer holds an arbitrary address, so reading or writing it is undefined.'),
          ],
          remediation: {
            explanation: 'A pointer is a house address written on a card. The card is not the house; * means go to that address and look inside. Two cards with the same address point to the same house, so changes through either are visible to both.',
            steps: ['Draw boxes for x and p with arrows for int x = 5; int *p = &x;.', 'Print x, &x, p and *p and explain each line of output.', 'Write swap using pointers and test it.'],
          },
        }),
        sub('c-arr', 'Arrays and strings', 'Array indexing, the array-pointer relationship, and null-terminated strings.', {
          points: ['Arrays are contiguous blocks with zero-based indexing', 'An array name decays to a pointer to its first element', 'C does not check bounds', 'Strings are char arrays ending in \'\\0\''],
          summary: [
            'An array stores elements of one type contiguously, indexed from 0. The name of an array usually decays to a pointer to its first element, so a[i] is equivalent to *(a + i). C performs no bounds checking: reading or writing past the end is undefined behaviour.',
            'A C string is an array of char terminated by the null character \'\\0\'. Functions such as strlen and strcpy rely on that terminator, so a buffer must be large enough for the text plus one extra byte.',
          ],
          cards: [fc('What marks the end of a C string?', 'The null character \'\\0\'.'), fc('What is a[i] equivalent to?', '*(a + i)'), fc('Does C check array bounds?', 'No. Out-of-bounds access is undefined behaviour.')],
          questions: [
            q('How many bytes are needed to store the string "hello" in a char array?', '6', ['5', '4', '7'], 'Five letters plus the terminating \'\\0\'.'),
            q('For an array a, what is a[2] equivalent to?', '*(a + 2)', ['&a + 2', 'a * 2', '*a + 2'], 'Indexing is pointer arithmetic followed by dereference.'),
            q('What happens if you write beyond the end of an array?', 'Undefined behaviour', ['A runtime exception is always thrown', 'The array grows', 'The extra write is ignored'], 'C does not check bounds, so the result is undefined.'),
            q('What does strlen("abc") return?', '3', ['4', '2', '0'], 'strlen counts characters up to, but not including, the null terminator.'),
          ],
          remediation: {
            explanation: 'An array is a row of equal-sized lockers numbered from 0. The row has no sign saying where it ends, so if you open locker 10 in a row of 5 you are opening someone else’s locker. A string is a row of lockers whose last locker always holds the end marker.',
            steps: ['Declare char s[6] = "hello"; and print each character with its index.', 'Predict what a[5] does for int a[5] and explain why it is unsafe.', 'Write your own strlen using a loop.'],
          },
        }),
        sub('c-heap', 'Dynamic memory', 'malloc, calloc, realloc and free; leaks and dangling pointers.', {
          points: ['malloc reserves bytes on the heap', 'Every successful allocation needs one free', 'Always check for a NULL return', 'Using memory after free is a dangling-pointer bug'],
          summary: [
            'Local variables live on the stack and vanish when a function returns. Memory you request with malloc lives on the heap until you release it with free. malloc returns NULL on failure, so check the result before use.',
            'Forgetting to free leaks memory; freeing twice or using memory after free corrupts the program. A good habit is to set a pointer to NULL after freeing it and to pair every allocation with a clearly owned free.',
          ],
          cards: [fc('What does malloc return on failure?', 'NULL.'), fc('What is a memory leak?', 'Heap memory that is no longer reachable but was never freed.'), fc('What is a dangling pointer?', 'A pointer to memory that has already been freed.')],
          questions: [
            q('Which call allocates space for 10 ints on the heap?', 'malloc(10 * sizeof(int))', ['malloc(10)', 'alloc(int, 10)', 'new int[10]'], 'malloc takes a size in bytes, so multiply by sizeof(int).'),
            q('What is a memory leak?', 'Allocated memory that is never released', ['Reading outside an array', 'Freeing memory twice', 'Using an uninitialised variable'], 'A leak occurs when heap memory is lost without being freed.'),
            q('What should you check right after calling malloc?', 'Whether the result is NULL', ['Whether it is zero-filled', 'Whether it is aligned to 8 bytes', 'Nothing'], 'malloc returns NULL if the request cannot be satisfied.'),
            q('What is wrong with using p after free(p)?', 'p is dangling and its use is undefined behaviour', ['Nothing, the data is preserved', 'p becomes NULL automatically', 'The program restarts'], 'free does not change p, but the memory it pointed to is no longer yours.'),
          ],
          remediation: {
            explanation: 'The heap is a storage unit you rent. malloc is signing the rental, free is returning the key. Forget to return it and you pay forever (leak). Keep using the unit after returning the key and you are trespassing (dangling pointer).',
            steps: ['Allocate an int array with malloc, fill it, print it and free it.', 'Add a NULL check and print an error if allocation fails.', 'Set the pointer to NULL after free and explain why that helps.'],
          },
        }),
      ],
    },
  ],
}
