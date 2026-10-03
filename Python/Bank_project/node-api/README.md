# Node.js bank API

This HTTP API uses the same `Bank.db` SQLite database as the Python terminal
and Tkinter apps. It requires Node.js 22.13 or newer and has no npm
dependencies.

From this directory, start the API with:

```powershell
npm start
```

The API listens on `http://127.0.0.1:3000`. Set `PORT` to use a different
port. It binds to localhost by default. Both the Node API and Python app can
be used with the same database.

## Routes

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| GET | `/api/health` | No | Check that the API is running |
| POST | `/api/accounts` | No | Create an account |
| POST | `/api/auth/login` | No | Sign in and receive a bearer token |
| POST | `/api/auth/logout` | Yes | Invalidate the current token |
| GET | `/api/me` | Yes | Get the signed-in customer |
| POST | `/api/pin` | Yes | Create a four-digit PIN |
| PUT | `/api/pin` | Yes | Update the PIN |
| POST | `/api/balance` | Yes | Check the balance using the PIN |
| POST | `/api/deposits` | Yes | Deposit funds |
| POST | `/api/withdrawals` | Yes | Withdraw funds using the PIN |
| POST | `/api/transfers` | Yes | Transfer funds using the PIN |
| GET | `/api/transactions` | Yes | Get transaction history (`?limit=10`, max 100) |

Account creation accepts JSON with `name`, `username`, `password`, `mobile`,
and `initialBalance`. Login accepts `username` and `password`. Authenticated
routes require `Authorization: Bearer <token>`. Deposit bodies use `amount`;
withdrawals use `amount` and `pin`; transfers use `recipientAccount`, `amount`,
and `pin`.

Example:

```powershell
$account = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:3000/api/accounts `
  -ContentType application/json `
  -Body '{"name":"Ada Lovelace","username":"ada","password":"longpassword","mobile":"1234567890","initialBalance":1000}'

$login = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:3000/api/auth/login `
  -ContentType application/json `
  -Body '{"username":"ada","password":"longpassword"}'

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:3000/api/deposits `
  -Headers @{ Authorization = "Bearer $($login.token)" } `
  -ContentType application/json `
  -Body '{"amount":250}'
```

Run the API tests with `npm test`.

This project is for learning and local development, not real banking. It
retains the existing database's plaintext password/PIN storage for compatibility
with the Python application, and API login tokens are held in memory and expire
when the server stops. Do not expose it to an untrusted network or use it with
real financial data.
