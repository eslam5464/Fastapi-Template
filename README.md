# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/eslam5464/Fastapi-Template/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                            |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------ | -------: | -------: | ------: | --------: |
| app/\_\_init\_\_.py                             |        0 |        0 |    100% |           |
| app/api/\_\_init\_\_.py                         |        0 |        0 |    100% |           |
| app/api/routes.py                               |        6 |        0 |    100% |           |
| app/api/v1/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| app/api/v1/deps/\_\_init\_\_.py                 |        0 |        0 |    100% |           |
| app/api/v1/deps/auth.py                         |       36 |        0 |    100% |           |
| app/api/v1/deps/items.py                        |        8 |        0 |    100% |           |
| app/api/v1/deps/rate\_limit.py                  |       41 |        0 |    100% |           |
| app/api/v1/deps/rate\_limit\_user.py            |       38 |        0 |    100% |           |
| app/api/v1/endpoints/\_\_init\_\_.py            |        0 |        0 |    100% |           |
| app/api/v1/endpoints/auth.py                    |       38 |        1 |     97% |       150 |
| app/api/v1/endpoints/items.py                   |       44 |        0 |    100% |           |
| app/api/v1/endpoints/user.py                    |       12 |        0 |    100% |           |
| app/api/v1/router.py                            |        8 |        0 |    100% |           |
| app/api/v2/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| app/api/v2/router.py                            |        2 |        0 |    100% |           |
| app/core/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| app/core/config.py                              |      113 |        9 |     92% |216-219, 278-282, 343, 358 |
| app/core/constants.py                           |       13 |        0 |    100% |           |
| app/core/credentials/\_\_init\_\_.py            |        0 |        0 |    100% |           |
| app/core/credentials/apple\_pay.py              |        7 |        0 |    100% |           |
| app/core/credentials/firebase.py                |       17 |        1 |     94% |        31 |
| app/core/db.py                                  |       14 |        0 |    100% |           |
| app/core/db\_sync.py                            |        5 |        0 |    100% |           |
| app/core/exceptions/base.py                     |       14 |        0 |    100% |           |
| app/core/exceptions/http\_exceptions.py         |       33 |        0 |    100% |           |
| app/core/logger.py                              |      163 |       46 |     72% |142-148, 153-154, 158-186, 190-214, 236, 286, 305, 395-396 |
| app/core/responses.py                           |       21 |        0 |    100% |           |
| app/core/types.py                               |        2 |        0 |    100% |           |
| app/core/utils.py                               |       12 |        0 |    100% |           |
| app/main.py                                     |       82 |        0 |    100% |           |
| app/middleware/\_\_init\_\_.py                  |        0 |        0 |    100% |           |
| app/middleware/csrf.py                          |       47 |        0 |    100% |           |
| app/middleware/logging.py                       |       45 |        4 |     91% |39, 45, 47, 49 |
| app/middleware/rate\_limit.py                   |       11 |        0 |    100% |           |
| app/middleware/security\_headers.py             |       31 |        1 |     97% |        67 |
| app/models/\_\_init\_\_.py                      |        4 |        0 |    100% |           |
| app/models/base.py                              |       37 |        4 |     89% |58, 72, 82, 92 |
| app/models/item.py                              |        8 |        0 |    100% |           |
| app/models/user.py                              |       10 |        0 |    100% |           |
| app/repos/\_\_init\_\_.py                       |        4 |        0 |    100% |           |
| app/repos/base.py                               |      110 |       13 |     88% |49-50, 252-256, 260-262, 320-321, 397 |
| app/repos/item.py                               |       17 |        0 |    100% |           |
| app/repos/user.py                               |       16 |        0 |    100% |           |
| app/schemas/\_\_init\_\_.py                     |        9 |        0 |    100% |           |
| app/schemas/back\_blaze\_bucket.py              |        5 |        0 |    100% |           |
| app/schemas/base.py                             |        7 |        0 |    100% |           |
| app/schemas/firebase.py                         |       18 |        0 |    100% |           |
| app/schemas/google\_bucket.py                   |       16 |        0 |    100% |           |
| app/schemas/health\_check.py                    |        2 |        0 |    100% |           |
| app/schemas/item.py                             |       12 |        0 |    100% |           |
| app/schemas/token.py                            |       19 |        2 |     89% |    16, 30 |
| app/schemas/user.py                             |       33 |        0 |    100% |           |
| app/services/auth\_service.py                   |      140 |       13 |     91% |69-73, 94, 184, 193-196, 379-380, 432-433 |
| app/services/back\_blaze\_b2.py                 |      229 |        4 |     98% |276, 319, 500-501 |
| app/services/cache/\_\_init\_\_.py              |        6 |        0 |    100% |           |
| app/services/cache/base.py                      |       56 |        0 |    100% |           |
| app/services/cache/decorators.py                |       22 |        0 |    100% |           |
| app/services/cache/manager.py                   |       33 |        0 |    100% |           |
| app/services/cache/rate\_limiter.py             |       78 |        3 |     96% | 64, 85-86 |
| app/services/cache/token\_blacklist.py          |       42 |        0 |    100% |           |
| app/services/email/\_\_init\_\_.py              |        0 |        0 |    100% |           |
| app/services/email/base.py                      |       25 |        0 |    100% |           |
| app/services/email/brevo.py                     |       72 |        6 |     92% |40, 72, 94, 98, 102, 124 |
| app/services/email/resend.py                    |       55 |        0 |    100% |           |
| app/services/exceptions/\_\_init\_\_.py         |        3 |        0 |    100% |           |
| app/services/exceptions/apple\_pay.py           |       37 |        4 |     89% |23, 88, 114, 140 |
| app/services/exceptions/backblaze.py            |       20 |        0 |    100% |           |
| app/services/exceptions/base.py                 |        4 |        0 |    100% |           |
| app/services/exceptions/email.py                |        6 |        0 |    100% |           |
| app/services/exceptions/firebase.py             |       13 |        1 |     92% |        19 |
| app/services/exceptions/gcs.py                  |       10 |        2 |     80% |    19, 28 |
| app/services/exceptions/rate\_limiter.py        |       13 |        2 |     85% |    19, 37 |
| app/services/firebase.py                        |      206 |       42 |     80% |38, 88, 137-157, 176, 210, 243, 271, 303, 340, 381-388, 424-431, 470-484, 502-519 |
| app/services/firestore.py                       |       94 |        0 |    100% |           |
| app/services/gcs.py                             |      125 |        4 |     97% |130, 174, 282, 357 |
| app/services/item\_service.py                   |       33 |        1 |     97% |        96 |
| app/services/payments/apple\_pay.py             |      285 |       47 |     84% |102, 118, 206, 213-218, 305-306, 398-399, 405-407, 461-471, 591-592, 621-642, 675-676, 829-831 |
| app/services/task\_queue/\_\_init\_\_.py        |        8 |        0 |    100% |           |
| app/services/task\_queue/celery\_config.py      |        9 |        1 |     89% |        30 |
| app/services/task\_queue/tasks/\_\_init\_\_.py  |        3 |        0 |    100% |           |
| app/services/task\_queue/tasks/health\_tasks.py |        4 |        0 |    100% |           |
| app/services/task\_queue/tasks/user\_tasks.py   |       27 |        0 |    100% |           |
| app/services/types/\_\_init\_\_.py              |        3 |        0 |    100% |           |
| app/services/types/auth.py                      |        5 |        0 |    100% |           |
| app/services/types/email.py                     |       77 |        4 |     95% |85, 99, 102-103 |
| app/web.py                                      |       13 |        0 |    100% |           |
| **TOTAL**                                       | **2946** |  **215** | **93%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/eslam5464/Fastapi-Template/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/eslam5464/Fastapi-Template/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/eslam5464/Fastapi-Template/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/eslam5464/Fastapi-Template/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Feslam5464%2FFastapi-Template%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/eslam5464/Fastapi-Template/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.