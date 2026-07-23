# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/eslam5464/Fastapi-Template/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                           |    Stmts |     Miss |   Cover |   Missing |
|----------------------------------------------- | -------: | -------: | ------: | --------: |
| app/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| app/api/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| app/api/routes.py                              |        6 |        0 |    100% |           |
| app/api/v1/\_\_init\_\_.py                     |        0 |        0 |    100% |           |
| app/api/v1/deps/\_\_init\_\_.py                |        0 |        0 |    100% |           |
| app/api/v1/deps/auth.py                        |       42 |        4 |     90% |96-97, 156-157 |
| app/api/v1/deps/rate\_limit.py                 |       69 |        0 |    100% |           |
| app/api/v1/endpoints/\_\_init\_\_.py           |        0 |        0 |    100% |           |
| app/api/v1/endpoints/auth.py                   |       35 |        1 |     97% |       128 |
| app/api/v1/endpoints/user.py                   |       11 |        0 |    100% |           |
| app/api/v1/router.py                           |        8 |        0 |    100% |           |
| app/api/v2/\_\_init\_\_.py                     |       11 |        1 |     91% |        44 |
| app/api/v2/router.py                           |        2 |        0 |    100% |           |
| app/core/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| app/core/config.py                             |      112 |       14 |     88% |172, 180-183, 238-242, 293-296, 308-311 |
| app/core/constants.py                          |       29 |        3 |     90% | 50, 73-74 |
| app/core/credentials.py                        |       23 |        1 |     96% |        64 |
| app/core/db.py                                 |       17 |        0 |    100% |           |
| app/core/exceptions/apple\_pay.py              |       37 |        4 |     89% |23, 88, 114, 140 |
| app/core/exceptions/back\_blaze\_exceptions.py |       20 |        0 |    100% |           |
| app/core/exceptions/base.py                    |       14 |        0 |    100% |           |
| app/core/exceptions/firebase\_exceptions.py    |       13 |        1 |     92% |        19 |
| app/core/exceptions/gcs\_exceptions.py         |       11 |        2 |     82% |    21, 30 |
| app/core/exceptions/http\_exceptions.py        |       33 |        0 |    100% |           |
| app/core/exceptions/rate\_limiter.py           |       13 |        2 |     85% |    19, 37 |
| app/core/logger.py                             |      157 |       55 |     65% |118-124, 129-132, 136-164, 168-192, 214, 286-287, 378-425 |
| app/core/responses.py                          |       21 |        0 |    100% |           |
| app/core/types.py                              |        2 |        0 |    100% |           |
| app/core/utils.py                              |       67 |        0 |    100% |           |
| app/main.py                                    |       68 |        0 |    100% |           |
| app/middleware/\_\_init\_\_.py                 |        0 |        0 |    100% |           |
| app/middleware/csrf.py                         |       47 |        0 |    100% |           |
| app/middleware/logging.py                      |       45 |        4 |     91% |39, 45, 47, 49 |
| app/middleware/rate\_limit.py                  |       11 |        0 |    100% |           |
| app/middleware/security\_headers.py            |       31 |        1 |     97% |        65 |
| app/models/\_\_init\_\_.py                     |        3 |        0 |    100% |           |
| app/models/base.py                             |       37 |        4 |     89% |58, 72, 82, 92 |
| app/models/user.py                             |       11 |        0 |    100% |           |
| app/repos/\_\_init\_\_.py                      |        3 |        0 |    100% |           |
| app/repos/base.py                              |      110 |       13 |     88% |51-52, 267-271, 275-277, 335-336, 412 |
| app/repos/user.py                              |       16 |        2 |     88% |    27, 42 |
| app/schemas/\_\_init\_\_.py                    |        8 |        0 |    100% |           |
| app/schemas/back\_blaze\_bucket.py             |        5 |        0 |    100% |           |
| app/schemas/base.py                            |        7 |        0 |    100% |           |
| app/schemas/firebase.py                        |       18 |        0 |    100% |           |
| app/schemas/google\_bucket.py                  |       16 |        0 |    100% |           |
| app/schemas/health\_check.py                   |        2 |        0 |    100% |           |
| app/schemas/token.py                           |       19 |        2 |     89% |    16, 30 |
| app/schemas/user.py                            |       33 |        0 |    100% |           |
| app/services/auth\_service.py                  |      140 |       26 |     81% |67-71, 92, 186, 195-198, 274-287, 316-325, 381-382, 430-431 |
| app/services/back\_blaze\_b2.py                |      229 |        4 |     98% |282, 325, 512-513 |
| app/services/cache/\_\_init\_\_.py             |        6 |        0 |    100% |           |
| app/services/cache/base.py                     |       45 |        0 |    100% |           |
| app/services/cache/decorators.py               |       17 |        0 |    100% |           |
| app/services/cache/manager.py                  |       60 |        0 |    100% |           |
| app/services/cache/rate\_limiter.py            |       67 |        0 |    100% |           |
| app/services/cache/token\_blacklist.py         |       62 |        0 |    100% |           |
| app/services/email/\_\_init\_\_.py             |        0 |        0 |    100% |           |
| app/services/email/base.py                     |       25 |        0 |    100% |           |
| app/services/email/brevo.py                    |       72 |        6 |     92% |40, 74, 96, 100, 106, 130 |
| app/services/email/resend.py                   |       55 |        0 |    100% |           |
| app/services/exceptions/\_\_init\_\_.py        |        4 |        0 |    100% |           |
| app/services/exceptions/auth.py                |        4 |        0 |    100% |           |
| app/services/exceptions/base.py                |        1 |        0 |    100% |           |
| app/services/exceptions/email.py               |        6 |        0 |    100% |           |
| app/services/firebase.py                       |      206 |       42 |     80% |38, 88, 137-157, 176, 210, 243, 273, 305, 342, 383-390, 426-433, 473-487, 505-522 |
| app/services/firestore.py                      |       94 |        0 |    100% |           |
| app/services/gcs.py                            |      125 |        4 |     97% |130, 174, 284, 363 |
| app/services/payments/apple\_pay.py            |      285 |       47 |     84% |90, 106, 196, 203-208, 303-304, 403-406, 412-414, 472-486, 614-615, 651-676, 711-712, 862-864 |
| app/services/types/\_\_init\_\_.py             |        3 |        0 |    100% |           |
| app/services/types/auth.py                     |        5 |        0 |    100% |           |
| app/services/types/email.py                    |       77 |        4 |     95% |78, 92, 95-96 |
| app/web.py                                     |       13 |        0 |    100% |           |
| **TOTAL**                                      | **2844** |  **247** | **91%** |           |


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