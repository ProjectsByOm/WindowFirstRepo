import { randomBytes } from "node:crypto";
import { createServer } from "node:http";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";
import path from "node:path";

const DEFAULT_DB_PATH = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "Bank.db",
);
const MAX_BODY_BYTES = 16 * 1024;

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function fail(status, message) {
  throw new ApiError(status, message);
}

function initializeDatabase(db) {
  db.exec("PRAGMA foreign_keys = ON; PRAGMA busy_timeout = 5000;");
  db.exec(`
    CREATE TABLE IF NOT EXISTS Customers(
      Id INTEGER PRIMARY KEY AUTOINCREMENT,
      Username TEXT UNIQUE NOT NULL,
      Password TEXT NOT NULL,
      Name TEXT NOT NULL,
      Mobile TEXT NOT NULL,
      Account INTEGER UNIQUE NOT NULL,
      Pin INTEGER,
      Balance INTEGER NOT NULL DEFAULT 0 CHECK(Balance >= 0)
    );
    CREATE TABLE IF NOT EXISTS Transactions(
      TransactionId INTEGER PRIMARY KEY AUTOINCREMENT,
      FromAccount INTEGER,
      ToAccount INTEGER,
      AmountTransferred INTEGER NOT NULL CHECK(AmountTransferred > 0),
      DateAndTime TEXT NOT NULL,
      Type TEXT NOT NULL DEFAULT 'Transfer',
      FOREIGN KEY (FromAccount) REFERENCES Customers(Account),
      FOREIGN KEY (ToAccount) REFERENCES Customers(Account)
    );
  `);

  const transactionColumns = new Set(
    db.prepare("PRAGMA table_info(Transactions)").all().map((column) => column.name),
  );
  if (!transactionColumns.has("Type")) {
    db.exec("ALTER TABLE Transactions ADD COLUMN Type TEXT NOT NULL DEFAULT 'Transfer'");
  }
}

function cleanCustomer(customer) {
  const { Password, Pin, ...publicFields } = customer;
  return publicFields;
}

function validatePin(pin) {
  if (typeof pin !== "string" || !/^\d{4}$/.test(pin)) {
    fail(400, "PIN must be exactly 4 digits.");
  }
  return Number(pin);
}

function validateAmount(amount, label, maximum) {
  if (!Number.isSafeInteger(amount) || amount <= 0) {
    fail(400, `${label} must be a whole number greater than zero.`);
  }
  if (amount > maximum) {
    fail(400, `${label} cannot exceed ${maximum}.`);
  }
  return amount;
}

function timestamp() {
  const date = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function recordTransaction(db, fromAccount, toAccount, amount, type) {
  db.prepare(`
    INSERT INTO Transactions (FromAccount, ToAccount, AmountTransferred, DateAndTime, Type)
    VALUES (?, ?, ?, ?, ?)
  `).run(fromAccount, toAccount, amount, timestamp(), type);
}

async function readJson(request) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > MAX_BODY_BYTES) {
      fail(413, "Request body is too large.");
    }
    chunks.push(chunk);
  }

  if (chunks.length === 0) {
    return {};
  }

  let body;
  try {
    body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    fail(400, "Request body must contain valid JSON.");
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    fail(400, "Request body must be a JSON object.");
  }
  return body;
}

function sendJson(response, status, body) {
  response.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(body));
}

export function createBankServer({ dbPath = DEFAULT_DB_PATH, logger = console } = {}) {
  const db = new DatabaseSync(dbPath);
  initializeDatabase(db);
  const sessions = new Map();

  const server = createServer(async (request, response) => {
    try {
      const url = new URL(request.url, "http://127.0.0.1");
      const method = request.method;
      const route = `${method} ${url.pathname}`;

      if (route === "GET /api/health") {
        sendJson(response, 200, { status: "ok" });
        return;
      }

      if (route === "POST /api/accounts") {
        const body = await readJson(request);
        const name = typeof body.name === "string" ? body.name.trim() : "";
        const username = typeof body.username === "string" ? body.username.trim() : "";
        const password = typeof body.password === "string" ? body.password.trim() : "";
        const mobile = typeof body.mobile === "string" ? body.mobile.trim() : "";
        const initialBalance = body.initialBalance;

        if (name.length < 3 || !/^[\p{L} ]+$/u.test(name)) {
          fail(400, "Name must be at least 3 characters and contain only letters.");
        }
        if (username.length < 3) {
          fail(400, "Username must be at least 3 characters long.");
        }
        if (password.length < 8) {
          fail(400, "Password must be at least 8 characters long.");
        }
        if (!/^\d{10}$/.test(mobile)) {
          fail(400, "Mobile number must contain exactly 10 digits.");
        }
        if (!Number.isSafeInteger(initialBalance) || initialBalance < 0 || initialBalance > 100000) {
          fail(400, "Initial deposit must be between 0 and 100000.");
        }
        if (db.prepare("SELECT 1 FROM Customers WHERE Username = ?").get(username)) {
          fail(409, "Username already exists. Please choose another one.");
        }

        let customerId;
        db.exec("BEGIN IMMEDIATE");
        try {
          const result = db.prepare(`
            INSERT INTO Customers (Username, Password, Name, Mobile, Account, Balance)
            VALUES (?, ?, ?, ?, 0, ?)
          `).run(username, password, name, mobile, initialBalance);
          customerId = Number(result.lastInsertRowid);
          const accountNumber = 1000000000 + customerId;
          db.prepare("UPDATE Customers SET Account = ? WHERE Id = ?").run(accountNumber, customerId);
          if (initialBalance > 0) {
            recordTransaction(db, null, accountNumber, initialBalance, "Deposit");
          }
          db.exec("COMMIT");
        } catch (error) {
          db.exec("ROLLBACK");
          if (error.code === "ERR_SQLITE_CONSTRAINT_UNIQUE") {
            fail(409, "Username already exists. Please choose another one.");
          }
          throw error;
        }

        sendJson(response, 201, {
          account: db.prepare("SELECT Account FROM Customers WHERE Id = ?").get(customerId).Account,
        });
        return;
      }

      if (route === "POST /api/auth/login") {
        const body = await readJson(request);
        if (typeof body.username !== "string" || typeof body.password !== "string") {
          fail(400, "Username and password are required.");
        }
        const customer = db.prepare("SELECT * FROM Customers WHERE Username = ?").get(body.username);
        if (!customer || customer.Password !== body.password) {
          fail(401, "Invalid username or password.");
        }
        const token = randomBytes(32).toString("hex");
        sessions.set(token, customer.Id);
        sendJson(response, 200, { token, customer: cleanCustomer(customer) });
        return;
      }

      const authorization = request.headers.authorization;
      const token = authorization?.startsWith("Bearer ") ? authorization.slice(7) : "";
      const customerId = sessions.get(token);

      if (route === "POST /api/auth/logout") {
        if (!customerId) {
          fail(401, "Authentication required.");
        }
        sessions.delete(token);
        sendJson(response, 200, { message: "Logged out." });
        return;
      }

      if (url.pathname.startsWith("/api/")) {
        if (!customerId) {
          fail(401, "Authentication required.");
        }
        const customer = db.prepare("SELECT * FROM Customers WHERE Id = ?").get(customerId);
        if (!customer) {
          sessions.delete(token);
          fail(401, "Account not found. Please sign in again.");
        }

        if (route === "GET /api/me") {
          sendJson(response, 200, { customer: cleanCustomer(customer) });
          return;
        }

        if (route === "POST /api/pin") {
          const body = await readJson(request);
          const pin = validatePin(body.pin);
          if (customer.Pin !== null) {
            fail(409, "PIN already exists. Use the update PIN option.");
          }
          db.prepare("UPDATE Customers SET Pin = ? WHERE Id = ?").run(pin, customerId);
          sendJson(response, 200, { message: "PIN created successfully." });
          return;
        }

        if (route === "PUT /api/pin") {
          const body = await readJson(request);
          const currentPin = validatePin(body.currentPin);
          const newPin = validatePin(body.newPin);
          if (customer.Pin === null) {
            fail(400, "No PIN has been created yet.");
          }
          if (currentPin !== customer.Pin) {
            fail(400, "Current PIN is incorrect.");
          }
          db.prepare("UPDATE Customers SET Pin = ? WHERE Id = ?").run(newPin, customerId);
          sendJson(response, 200, { message: "PIN updated successfully." });
          return;
        }

        if (route === "POST /api/balance") {
          const body = await readJson(request);
          const pin = validatePin(body.pin);
          if (customer.Pin === null) {
            fail(400, "PIN has not been created for this account.");
          }
          if (pin !== customer.Pin) {
            fail(400, "Wrong PIN.");
          }
          sendJson(response, 200, { balance: customer.Balance });
          return;
        }

        if (route === "POST /api/deposits") {
          const body = await readJson(request);
          const amount = validateAmount(body.amount, "Deposit amount", 500000);
          db.exec("BEGIN IMMEDIATE");
          try {
            const account = db.prepare("SELECT Account, Balance FROM Customers WHERE Id = ?").get(customerId);
            if (!account) {
              fail(404, "Account not found.");
            }
            const currentBalance = account.Balance;
            const newBalance = currentBalance + amount;
            if (!Number.isSafeInteger(newBalance)) {
              fail(400, "The resulting balance is too large.");
            }
            db.prepare("UPDATE Customers SET Balance = Balance + ? WHERE Id = ?").run(amount, customerId);
            recordTransaction(db, null, account.Account, amount, "Deposit");
            db.exec("COMMIT");
            sendJson(response, 200, { balance: newBalance });
          } catch (error) {
            db.exec("ROLLBACK");
            throw error;
          }
          return;
        }

        if (route === "POST /api/withdrawals") {
          const body = await readJson(request);
          const amount = validateAmount(body.amount, "Withdrawal amount", 10000);
          const pin = validatePin(body.pin);
          db.exec("BEGIN IMMEDIATE");
          let newBalance;
          try {
            const account = db.prepare("SELECT Account, Pin, Balance FROM Customers WHERE Id = ?").get(customerId);
            if (!account) {
              fail(404, "Account not found.");
            }
            if (account.Pin === null) {
              fail(400, "PIN not created for this account.");
            }
            if (pin !== account.Pin) {
              fail(400, "Wrong PIN.");
            }
            if (amount > account.Balance) {
              fail(400, "Insufficient balance.");
            }
            newBalance = account.Balance - amount;
            db.prepare("UPDATE Customers SET Balance = Balance - ? WHERE Id = ?").run(amount, customerId);
            recordTransaction(db, account.Account, null, amount, "Withdrawal");
            db.exec("COMMIT");
          } catch (error) {
            db.exec("ROLLBACK");
            throw error;
          }
          sendJson(response, 200, { balance: newBalance });
          return;
        }

        if (route === "POST /api/transfers") {
          const body = await readJson(request);
          const recipientAccount = body.recipientAccount;
          const amount = validateAmount(body.amount, "Transfer amount", 100000);
          const pin = validatePin(body.pin);
          if (!Number.isSafeInteger(recipientAccount)) {
            fail(400, "Recipient account number must be a whole number.");
          }
          db.exec("BEGIN IMMEDIATE");
          try {
            const sender = db.prepare("SELECT Id, Account, Pin, Balance FROM Customers WHERE Id = ?").get(customerId);
            if (!sender) {
              fail(404, "Account not found.");
            }
            if (sender.Pin === null) {
              fail(400, "PIN not created for this account.");
            }
            if (pin !== sender.Pin) {
              fail(400, "Wrong PIN.");
            }
            if (sender.Account === recipientAccount) {
              fail(400, "You cannot transfer money to your own account.");
            }
            const recipient = db.prepare("SELECT Id, Account FROM Customers WHERE Account = ?").get(recipientAccount);
            if (!recipient) {
              fail(404, "Recipient account not found.");
            }
            if (sender.Balance < amount) {
              fail(400, "Insufficient balance for this transfer.");
            }
            db.prepare("UPDATE Customers SET Balance = Balance - ? WHERE Id = ?").run(amount, customerId);
            db.prepare("UPDATE Customers SET Balance = Balance + ? WHERE Id = ?").run(amount, recipient.Id);
            recordTransaction(db, sender.Account, recipient.Account, amount, "Transfer");
            db.exec("COMMIT");
          } catch (error) {
            db.exec("ROLLBACK");
            throw error;
          }
          sendJson(response, 200, { message: `Transfer successful. ${amount} sent to account ${recipientAccount}.` });
          return;
        }

        if (route === "GET /api/transactions") {
          const requestedLimit = url.searchParams.get("limit");
          const limit = requestedLimit === null ? 10 : Number(requestedLimit);
          if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
            fail(400, "Transaction limit must be between 1 and 100.");
          }
          const transactions = db.prepare(`
            SELECT * FROM Transactions
            WHERE FromAccount = ? OR ToAccount = ?
            ORDER BY TransactionId DESC
            LIMIT ?
          `).all(customer.Account, customer.Account, limit);
          sendJson(response, 200, { transactions });
          return;
        }
      }

      fail(404, "Route not found.");
    } catch (error) {
      if (error instanceof ApiError) {
        sendJson(response, error.status, { error: error.message });
        return;
      }
      logger.error("Bank API request failed:", error);
      if (!response.headersSent) {
        sendJson(response, 500, { error: "Internal server error." });
      } else {
        response.destroy(error);
      }
    }
  });

  server.on("close", () => db.close());
  return server;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT ?? 3000);
  if (!Number.isInteger(port) || port < 0 || port > 65535) {
    console.error("PORT must be an integer between 0 and 65535.");
    process.exitCode = 1;
  } else {
    const server = createBankServer();
    server.listen(port, "127.0.0.1", () => {
      const address = server.address();
      console.log(`Bank API listening at http://127.0.0.1:${address.port}`);
    });
    for (const signal of ["SIGINT", "SIGTERM"]) {
      process.on(signal, () => server.close());
    }
  }
}
