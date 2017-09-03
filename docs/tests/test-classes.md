Overview of what is provided by the base test classes.

**NOTE**: It is easy for documentation to get out of sync with code. If anything in here doesn't seem to match the results you're getting, take a look at the source:

| Location | Contains |
|----------|----------|
| [`sjfnw/tests/base.py`](https://github.com/aisapatino/sjfnw/blob/master/sjfnw/tests/base.py) | `BaseTestCase` |
| [`sjfnw/fund/fixtures/`](https://github.com/aisapatino/sjfnw/blob/master/sjfnw/fund/fixtures) | fixtures for fund models |
| [`sjfnw/fund/tests/base.py`](https://github.com/aisapatino/sjfnw/blob/master/sjfnw/fund/tests/base.py) | `BaseFundTestCase` |
| [`sjfnw/grants/fixtures/`](https://github.com/aisapatino/sjfnw/blob/master/sjfnw/grants/fixtures) | fixtures for grants models |
| [`sjfnw/grants/tests/base.py`](https://github.com/aisapatino/sjfnw/blob/master/sjfnw/grants/tests/base.py) | `BaseGrantTestCase` |

## Overview

See [`intro-to-testing`](intro-to-testing.md) for information about what Python/Django test cases provide. This page goes over sjfnw-specific customizations.

TestCase inheritance (a → b means a inherits b)

```
                              unittest.TestCase
                                      ↑
                            django.test.TestCase
                                      ↑
                        sjfnw.tests.base.BaseTestCase
                          ↑                      ↑
sjfnw.fund.tests.base.BaseFundTestCase   sjfnw.grants.tests.base.BaseGrantTestCase
```

## `BaseTestCase`

This class provides some basic conveniences that are relevant to both fund and grants tests.

### Account shortcuts

#### `self.login_as_admin()`

Logs in as a superuser (a user that can access the admin account). Has no associated `Member` or `Organization`.

#### `self.login_as_member(name)`

Shortcut for logging in as one of a few pre-defined members. It creates the necessary objects (`Member`, `Membership`(s), `Donor`(s), etc.) and then log the test user in.  It also sets `self.member_id` with the primary key of the `Member` object.

##### 'first'

- Email: `firstacct@gmail.com`
- If `sjfnw/fund/fixtures/test_fund.json` is used:
  - It has a membership and 8 donors - see `sjfnw/fund/fixtures/test_fund.json` for details
  - `self.member_id` and `self.ship_id` will be set

##### 'blank'

- Email: `blankacct@gmail.com`
- No memberships or other objects associated


`BaseFundTestCase` expands upon this method, supporting a few additional names. See below for details.

### Custom asserts

#### `assert_message(response, text, regex=False)`

Assert that the given text has been set on the response as a message (via `django.contrib.messages`)

#### `assert_length(collection, expected_length)`

Assert that the given collection (list, dictionary, or anything that `len()` can be called on) has the expected length. Gives a more informative error message than using a plain `assertEqual`:

```py
assertEqual(len(my_list), 3) # AssertionError: 1 != 3
assert_length(my_list, 3)    # AssertionError: Expected ['a'] to have length of 3, but got 1
```

#### `assert_count(queryset, expected_count)`

Calls `.count()` on the given queryset and asserts that it matches the expected number. Gives a more informative error message than using a plain `assertEqual`:

```py
assertEqual(qs.count(), 2) # AssertionError: 0 != 2
assert_length(qs, 2)       # AssertionError: Expected queryset count to be 2, but got 0
```

## `BaseFundTestCase`

### Fixtures

By inheriting, your test will use the fixtures specified by `BaseFundTestCase` unless you overwrite that property.

### `setUp` - creates 2 giving projects

Creates:

- Post-training GP (Fundraising training date has passed; estimates are required)
- Pre-training GP (Fundraising training has not happened; estimates not required)

### `login_as_member`

Additional options for the method provided by `BaseTestCase`:

#### 'current'

- Email: `testacct@gmail.com`
- Membership in Post-training project
- One Donor (`self.donor_id`) with one incomplete, overdue step (`self.step_id`)

#### 'new'

- `newacct@gmail.com`
- 2 Memberships:
    - Pre-training (`self.pre_id` or `self.ship_id`) _default_
    - Post-training (`self.post_id`)
- No Donors

_default_ means that `member.current` is set to that membership, so it will be used when the user logs into Project Central.

## TODO - `BaseGrantTestCase`
