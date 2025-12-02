from .humaneval_runner import run_function

# TASKS = [
#     # name, file, func, list of (args, expected)
#     ("add", "add.exp", "add", [([1, 2], 3), ([0, 0], 0)]),
#     ("max", "max.exp", "max", [([5, 3], 5), ([4, 7], 7)]),
# ]

TASKS = [
    # name, file, func, list of (args, expected)

    ("add", "add.exp", "add",
     [([1, 2], 3), ([0, 0], 0), ([-1, 5], 4)]),

    ("max", "max.exp", "max",
     [([5, 3], 5), ([4, 7], 7)]),

    ("square", "square.exp", "square",
     [([0], 0), ([2], 4), ([3], 9), ([-2], 4)]),

    ("absval", "absval.exp", "absval",
     [([5], 5), ([-7], 7), ([0], 0)]),

    ("min", "min.exp", "min",
     [([5, 3], 3), ([4, 7], 4)]),

    ("clamp_zero", "clamp_zero.exp", "clamp_zero",
     [([-5], 0), ([3], 3)]),

    ("signum", "signum.exp", "signum",
     [([10], 1), ([-3], -1), ([0], 0)]),

    ("is_even", "is_even.exp", "is_even",
     [([4], 1), ([5], 0)]),

    ("is_odd", "is_odd.exp", "is_odd",
     [([4], 0), ([5], 1)]),

    ("max3", "max3.exp", "max3",
     [([1, 2, 3], 3), ([10, 2, 3], 10), ([-1, -5, -3], -1)]),

    ("min3", "min3.exp", "min3",
     [([1, 2, 3], 1), ([10, 2, 3], 2), ([-1, -5, -3], -5)]),

    ("clamp_range", "clamp_range.exp", "clamp_range",
     [([5, 0, 10], 5), ([-3, 0, 10], 0), ([20, 0, 10], 10)]),

    ("add3", "add3.exp", "add3",
     [([1, 2, 3], 6)]),

    ("mul3", "mul3.exp", "mul3",
     [([2, 3, 4], 24)]),

    ("average2", "average2.exp", "average2",
     [([3, 5], 4.0), ([2, 3], 2.5)]),

    ("diff", "diff.exp", "diff",
     [([7, 3], 4), ([3, 7], 4)]),

    ("is_nonzero", "is_nonzero.exp", "is_nonzero",
     [([0], 0), ([7], 1), ([-3], 1)]),

    ("is_between", "is_between.exp", "is_between",
     [([5, 0, 10], 1), ([-1, 0, 10], 0), ([11, 0, 10], 0)]),

    ("is_positive", "is_positive.exp", "is_positive",
     [([5], 1), ([0], 0), ([-3], 0)]),

    ("same_parity", "same_parity.exp", "same_parity",
     [([2, 4], 1), ([2, 3], 0), ([5, 7], 1)]),

<<<<<<< HEAD
    ("is_prime", "is_prime.exp", "is_prime",
     [([2], 1), ([3], 1), ([4], 0), ([17], 1), ([1], 0)]),

    ("sum_digits", "sum_digits.exp", "sum_digits",
     [([123], 6), ([0], 0), ([999], 27)]),

    ("is_palindrome", "is_palindrome.exp", "is_palindrome",
     [([121], 1), ([123], 0), ([9], 1)]),

=======
    ("dot", "dot_product.exp", "dot", [
        ([[1, 2, 3], [4, 5, 6]], 32),
        ([[0, 0, 0], [7, 8, 9]], 0),
    ]),

    ("sum_array", "reverse_number.exp", "sum_array", [
        ([[1, 2, 3, 4], 4], 10),
        ([[0, 0, 0], 3], 0),
        ([[-1, 2, -3, 4], 4], 2),
    ]),

    ("matrix_sum", "matrix_sum.exp", "matrix_sum", [
        ([[[1, 2], [3, 4]]], 10),
        ([[[0, 0], [0, 0]]], 0),
        ([[[-1, 2], [-3, 4]]], 2),
    ]),
>>>>>>> work-with-data
]

def main():
    total = len(TASKS)
    type_ok = 0
    runtime_ok = 0
    fully_correct = 0
    total_tests = 0
    total_passed = 0

    for name, filename, func, tests in TASKS:
        print(f"=== {name} ===")
        task_type_ok = True
        task_runtime_ok = True
        task_all_correct = True

        for args, expected in tests:
            total_tests += 1
            try:
                got = run_function(filename, func, args)
            except Exception as e:
                # could be parser/type error or runtime error; classify crudely
                task_all_correct = False
                task_runtime_ok = False
                task_type_ok = False
                print(f"  ERROR on {args}: {e}")
                break  # stop testing this task

            if got != expected:
                task_all_correct = False
                print(f"  FAIL {args} -> {got}, expected {expected}")
            else:
                total_passed += 1
                print(f"  OK   {args} -> {got}")

        if task_type_ok:
            type_ok += 1
        if task_runtime_ok:
            runtime_ok += 1
        if task_all_correct:
            fully_correct += 1

    print("\n=== Metrics ===")
    print(f"Tasks: {total}")
    print(f"A (type+parse success): {type_ok}/{total}")
    print(f"B (no runtime errors on tested inputs): {runtime_ok}/{total}")
    print(f"C1 (tasks fully correct): {fully_correct}/{total}")
    print(f"C2 (per-test accuracy): {total_passed}/{total_tests}")

# A: parse + type inference success rate
# B: runtime success rate
# C: functional correctness / end-to-end success rate

if __name__ == "__main__":
    main()