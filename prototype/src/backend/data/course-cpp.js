import { q, fc, sub } from './helpers.js'

export const courseCpp = {
  id: 'cpp-cs201',
  code: 'CS 201',
  title: 'Object-Oriented Programming in C++',
  department: 'Computer Science',
  credits: 4,
  level: 'Undergraduate · Year 2',
  accent: '#2b5565',
  description:
    'Object-oriented design with C++: classes, inheritance, polymorphism and the Standard Template Library.',
  instructorId: 'u-rao',
  status: 'published',
  source: { fileName: 'CS201-syllabus.pdf' },
  topics: [
    {
      id: 'cpp-t1',
      title: 'Classes and Objects',
      subtopics: [
        sub('cpp-class', 'Classes and encapsulation', 'Defining classes, members, access specifiers and hiding implementation details.', {
          points: ['A class bundles data and the functions that act on it', 'private members are accessible only inside the class', 'public members form the interface', 'struct defaults to public, class defaults to private'],
          summary: [
            'A class combines data members and member functions into one type. Access specifiers control visibility: private members can only be used by the class itself, public members form its interface. Hiding data behind functions is called encapsulation and lets you change the implementation without breaking callers.',
            'In C++ the only difference between struct and class is the default access: struct members are public by default, class members are private. By convention, struct is used for plain data and class for types with behaviour and invariants.',
          ],
          cards: [fc('What is encapsulation?', 'Bundling data with its functions and hiding the internals behind a public interface.'), fc('Default access of a class member?', 'private.'), fc('Default access of a struct member?', 'public.')],
          questions: [
            q('What is the default access of members in a C++ class?', 'private', ['public', 'protected', 'There is no default'], 'Members of a class are private unless declared otherwise.'),
            q('What is the main benefit of encapsulation?', 'The implementation can change without affecting callers', ['Programs run faster', 'Memory use is reduced', 'Inheritance becomes unnecessary'], 'Callers depend only on the public interface.'),
            q('How does struct differ from class in C++?', 'Default member access is public instead of private', ['Structs cannot have functions', 'Structs cannot be inherited', 'Structs are stored on the stack only'], 'The only language-level difference is default access (and default inheritance access).'),
            q('Which members can code outside the class access directly?', 'public members', ['private members', 'All members', 'Only static members'], 'Only public members are accessible from outside the class.'),
          ],
          remediation: {
            explanation: 'Think of a vending machine. You use the buttons (public interface) and never reach into the machinery (private data). The owner can swap the machinery without changing how you use the buttons.',
            steps: ['Write a BankAccount class with a private balance and public deposit() and balance() functions.', 'Try to access balance directly from main and read the compiler error.', 'Change class to struct and note what changes.'],
          },
        }),
        sub('cpp-ctor', 'Constructors and destructors', 'Object initialisation, member initialiser lists, destructors and RAII.', {
          points: ['A constructor runs when an object is created', 'Initialiser lists initialise members before the body runs', 'A destructor runs when an object’s lifetime ends', 'RAII ties resource release to object lifetime'],
          summary: [
            'A constructor has the class name and no return type; it runs automatically when an object is created and puts it in a valid state. Member initialiser lists (Point(int x, int y) : x_(x), y_(y) {}) initialise members directly and are required for const and reference members.',
            'A destructor, written ~ClassName(), runs when the object goes out of scope or is deleted. RAII (resource acquisition is initialisation) uses this: acquire a resource in the constructor and release it in the destructor, so cleanup happens automatically even when exceptions occur.',
          ],
          cards: [fc('When does a destructor run?', 'When the object’s lifetime ends: leaving scope or delete.'), fc('What is RAII?', 'Tying a resource’s acquisition and release to an object’s constructor and destructor.'), fc('Why use an initialiser list?', 'It initialises members directly, and is required for const and reference members.')],
          questions: [
            q('When is a destructor called for a local object?', 'When it goes out of scope', ['When the program starts', 'Only when delete is called', 'Never automatically'], 'Local objects are destroyed automatically at the end of their scope.'),
            q('What does RAII stand for?', 'Resource Acquisition Is Initialisation', ['Runtime Allocation Is Immediate', 'Reference And Instance Initialisation', 'Resource Allocation In Inheritance'], 'Resources are acquired in the constructor and released in the destructor.'),
            q('Which members must be set in a constructor initialiser list?', 'const and reference members', ['Only public members', 'Only static members', 'Pointer members'], 'They cannot be assigned after construction, so they must be initialised.'),
            q('What is the return type of a constructor?', 'It has none', ['void', 'The class type', 'int'], 'Constructors are declared without any return type.'),
          ],
          remediation: {
            explanation: 'A constructor is the check-in desk: everyone arriving is set up properly. A destructor is check-out: it tidies up. RAII says: let the desk do the tidying, instead of relying on people to remember.',
            steps: ['Write a class that prints a message in its constructor and destructor and create it in a nested scope.', 'Add a const member and set it via an initialiser list.', 'Wrap a file handle in a class so it always closes.'],
          },
        }),
      ],
    },
    {
      id: 'cpp-t2',
      title: 'Inheritance and Polymorphism',
      subtopics: [
        sub('cpp-inh', 'Inheritance', 'Base and derived classes, access control in inheritance and constructor order.', {
          points: ['A derived class reuses and extends a base class', 'Base constructors run before derived constructors', 'protected members are visible to derived classes', 'Use inheritance for "is-a" relationships'],
          summary: [
            'Inheritance lets a derived class reuse and extend a base class: class Dog : public Animal. It models an "is-a" relationship; a Dog is an Animal. protected members are accessible inside the class and its derived classes but not from outside.',
            'When a derived object is created the base-class constructor runs first, then the derived constructor. Destruction happens in the opposite order. Prefer composition (has-a) when the relationship is not truly is-a.',
          ],
          cards: [fc('Which constructor runs first for a derived object?', 'The base-class constructor.'), fc('What does protected allow?', 'Access from the class itself and its derived classes, but not from outside.'), fc('Inheritance models which relationship?', '"is-a".')],
          questions: [
            q('In what order are constructors called when creating a derived object?', 'Base first, then derived', ['Derived first, then base', 'Only the derived constructor', 'In alphabetical order'], 'The base part must exist before the derived part is initialised.'),
            q('Who can access a protected member?', 'The class and its derived classes', ['Anyone', 'Only the class itself', 'Only friends of main'], 'protected extends private access to derived classes.'),
            q('Which relationship does public inheritance model?', 'is-a', ['has-a', 'uses-a', 'owns-a'], 'Public inheritance means a derived object can be used wherever a base is expected.'),
            q('Which is generally preferred when classes are not truly is-a?', 'Composition', ['Multiple inheritance', 'Global variables', 'Friend functions'], 'Composition models has-a and avoids tight coupling.'),
          ],
          remediation: {
            explanation: 'A Dog is an Animal, so it gets everything an Animal has plus its own extras, just as a student ID card has everything a basic ID has plus a library number. If the relationship reads naturally as "has a", such as a Car having an Engine, use a member instead.',
            steps: ['Create Animal and Dog classes and print from both constructors to see the order.', 'Make a base member protected and use it from the derived class.', 'Decide whether Car/Engine should use inheritance or composition and justify it.'],
          },
        }),
        sub('cpp-virt', 'Virtual functions and polymorphism', 'Dynamic dispatch, virtual destructors and abstract classes.', {
          points: ['A virtual function is resolved at run time via the object’s real type', 'Calls through base pointers or references need virtual to dispatch correctly', 'Base classes with virtual functions need virtual destructors', 'A pure virtual function makes a class abstract'],
          summary: [
            'Marking a base function virtual lets a call through a base pointer or reference run the derived override. This run-time choice is called dynamic dispatch and is the core of polymorphism. Use the override keyword to catch signature mistakes.',
            'Deleting a derived object through a base pointer requires a virtual destructor, otherwise the derived destructor is skipped. A function declared = 0 is pure virtual; a class with one is abstract and cannot be instantiated, acting as an interface.',
          ],
          cards: [fc('What is dynamic dispatch?', 'Choosing which function to call at run time based on the object’s real type.'), fc('What does = 0 after a function declaration mean?', 'It is pure virtual; the class becomes abstract.'), fc('Why a virtual destructor?', 'So deleting through a base pointer runs the derived destructor too.')],
          questions: [
            q('A base-class function is not virtual. A call through a base pointer to a derived object runs which version?', 'The base-class version', ['The derived version', 'Neither, it is a compile error', 'Both'], 'Without virtual, the function is chosen from the static type of the pointer.'),
            q('Why should polymorphic base classes have a virtual destructor?', 'So derived destructors run when deleting via a base pointer', ['To make objects smaller', 'To allow copying', 'To prevent inheritance'], 'Otherwise deleting through the base pointer is undefined behaviour.'),
            q('What is an abstract class?', 'A class with at least one pure virtual function', ['A class with only private members', 'A class without constructors', 'A class declared in a header'], 'Abstract classes cannot be instantiated and define an interface.'),
            q('What does the override keyword do?', 'Makes the compiler verify that the function overrides a virtual one', ['Makes the function run faster', 'Hides the base function', 'Makes the function static'], 'It turns signature mismatches into compile errors.'),
          ],
          remediation: {
            explanation: 'Imagine a remote control that works with any brand of TV. You press "power" and each TV does its own thing. virtual is what makes the button reach the right TV at run time.',
            steps: ['Create Shape with virtual area() and Circle/Square overrides; call area() through Shape*.', 'Remove virtual and observe the difference.', 'Make Shape abstract with area() = 0.'],
          },
        }),
      ],
    },
    {
      id: 'cpp-t3',
      title: 'Standard Template Library',
      subtopics: [
        sub('cpp-vec', 'Vectors and iterators', 'std::vector, dynamic resizing and iterating with iterators and range-for.', {
          points: ['std::vector is a resizable array', 'push_back appends and may reallocate', 'Iterators generalise pointers over containers', 'Range-based for loops are the simplest way to traverse'],
          summary: [
            'std::vector stores elements contiguously and grows as needed. push_back appends, size() reports the count and operator[] gives fast indexed access. When capacity is exceeded the vector reallocates, which invalidates existing iterators and references.',
            'Iterators are pointer-like objects that let algorithms traverse any container. begin() points to the first element and end() one past the last. A range-based for loop (for (auto& x : v)) is the easiest way to visit every element.',
          ],
          cards: [fc('What does end() point to?', 'One past the last element.'), fc('Why can push_back invalidate iterators?', 'The vector may reallocate to a larger block.'), fc('Fastest way to loop over every element?', 'A range-based for loop: for (auto& x : v).')],
          questions: [
            q('What can happen to iterators when push_back triggers a reallocation?', 'They become invalid', ['They move to the end', 'They stay valid', 'They are converted to pointers'], 'Reallocation moves the elements, so old iterators point to freed memory.'),
            q('What does v.end() return?', 'An iterator one past the last element', ['An iterator to the last element', 'The size of the vector', 'A null pointer'], 'end() is a sentinel and must not be dereferenced.'),
            q('Which container is a resizable contiguous array?', 'std::vector', ['std::list', 'std::map', 'std::set'], 'vector stores its elements contiguously.'),
            q('Which loop visits every element of vector v by reference?', 'for (auto& x : v)', ['for (x in v)', 'foreach (x : v)', 'for (auto x = v)'], 'The range-based for with auto& avoids copying elements.'),
          ],
          remediation: {
            explanation: 'A vector is a row of seats that can be extended by moving everyone to a longer row. If you were holding a note of someone’s seat number (an iterator) before the move, the note is now wrong.',
            steps: ['Fill a vector with push_back and print size and capacity after each insert.', 'Store begin() in a variable, push_back many items, and explain why it is unsafe.', 'Rewrite an index loop as a range-based for.'],
          },
        }),
        sub('cpp-map', 'Maps and algorithms', 'std::map and unordered_map, plus sort and find from <algorithm>.', {
          points: ['std::map stores sorted key-value pairs', 'std::unordered_map offers average O(1) lookup by hashing', 'operator[] inserts a default value for a missing key', 'Algorithms like std::sort work on iterator ranges'],
          summary: [
            'std::map keeps key-value pairs sorted by key (a balanced tree, O(log n) operations). std::unordered_map hashes keys for average O(1) lookup but has no ordering. Note that m[key] inserts a default-constructed value when the key is missing; use find() or count() to test without inserting.',
            'The <algorithm> header provides generic functions such as std::sort, std::find and std::count that work on an iterator range [begin, end). Separating containers from algorithms is the central idea of the STL.',
          ],
          cards: [fc('Lookup complexity of std::map?', 'O(log n).'), fc('What does m[key] do for a missing key?', 'Inserts a default value for that key.'), fc('How do algorithms operate on containers?', 'Through iterator ranges [begin, end).')],
          questions: [
            q('What does m[k] do if k is not in a std::map?', 'Inserts k with a default-constructed value', ['Throws an exception', 'Returns null', 'Does nothing'], 'operator[] always ensures the key exists.'),
            q('Which container offers average O(1) lookup by key?', 'std::unordered_map', ['std::map', 'std::vector', 'std::set'], 'unordered_map uses hashing.'),
            q('How is std::map ordered?', 'By key', ['By insertion time', 'By value', 'Randomly'], 'map keeps keys sorted.'),
            q('Which call sorts a vector v ascending?', 'std::sort(v.begin(), v.end())', ['v.sort()', 'std::sort(v)', 'sort(v.end(), v.begin())'], 'std::sort takes a begin/end iterator pair.'),
          ],
          remediation: {
            explanation: 'A map is a dictionary: look up a word, get its meaning. std::map keeps the words alphabetised; unordered_map is a filing cabinet that jumps straight to the right drawer. Algorithms are tools that work on any shelf you point them at.',
            steps: ['Count word frequencies using std::unordered_map.', 'Show the difference between m[k] and m.find(k) for a missing key.', 'Sort a vector of structs by one field using std::sort.'],
          },
        }),
      ],
    },
  ],
}
