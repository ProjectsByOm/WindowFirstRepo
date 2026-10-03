import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import { DatabaseSync } from "node:sqlite";
import { createBankServer } from "./server.js";

let directory;
let dbPath;
let server;
let baseUrl;
let token;
let account;

before(async () => {
  directory = mkdtempSync(path.join(tmpdir(), "bank-api-"));
  dbPath = path.join(directory, "Bank.db");
  server = createBankServer({ dbPath, logger: { error() {} } });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  await new Promise((resolve) => server.close(resolve));
  rmSync(directory, { recursive: true, force: true });
});

async function request(route, { method = "GET", body, auth = true } = {}) {
  const headers = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (auth && token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${baseUrl}${route}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return { status: response.status, body: await response.json() };
}

test("serves a health check without authentication", async () => {
  assert.deepEqual(await request("/api/health", { auth: false }), {
    status: 200,
    body: { status: "ok" },
  });
});

test("creates accounts and signs in without exposing credentials or PIN", async () => {
  const created = await request("/api/accounts", {
    method: "POST",
    auth: false,
    body: {
      name: "Ada Lovelace",
      username: "ada-test",
      password: "longpassword",
      mobile: "1234567890",
      initialBalance: 1000,
    },
  });
  assert.equal(created.status, 201);
  account = created.body.account;

  const login = await request("/api/auth/login", {
    method: "POST",
    auth: false,
    body: { username: "ada-test", password: "longpassword" },
  });
  assert.equal(login.status, 200);
  token = login.body.token;
  assert.equal(login.body.customer.Account, account);
  assert.equal("Password" in login.body.customer, false);
  assert.equal("Pin" in login.body.customer, false);
});

test("requires authentication and enforces the PIN for balance", async () => {
  assert.equal((await request("/api/me", { auth: false })).status, 401);
  assert.deepEqual(await request("/api/pin", {
    method: "POST",
    body: { pin: "0123" },
  }), { status: 200, body: { message: "PIN created successfully." } });
  assert.deepEqual(await request("/api/balance", {
    method: "POST",
    body: { pin: "0123" },
  }), { status: 200, body: { balance: 1000 } });
  assert.equal((await request("/api/balance", {
    method: "POST",
    body: { pin: "9999" },
  })).status, 400);
});

test("records deposits, withdrawals, and transactions in the shared SQLite schema", async () => {
  const recipient = await request("/api/accounts", {
    method: "POST",
    auth: false,
    body: {
      name: "Grace Hopper",
      username: "grace-test",
      password: "anotherpassword",
      mobile: "0987654321",
      initialBalance: 50,
    },
  });
  assert.equal(recipient.status, 201);

  const deposit = await request("/api/deposits", {
    method: "POST",
    body: { amount: 200 },
  });
  assert.deepEqual(deposit, { status: 200, body: { balance: 1200 } });

  const withdrawal = await request("/api/withdrawals", {
    method: "POST",
    body: { amount: 50, pin: "0123" },
  });
  assert.deepEqual(withdrawal, { status: 200, body: { balance: 1150 } });

  const transfer = await request("/api/transfers", {
    method: "POST",
    body: { recipientAccount: recipient.body.account, amount: 100, pin: "0123" },
  });
  assert.equal(transfer.status, 200);

  const history = await request("/api/transactions");
  assert.equal(history.status, 200);
  assert.deepEqual(history.body.transactions.map(({ Type }) => Type), [
    "Transfer",
    "Withdrawal",
    "Deposit",
    "Deposit",
  ]);

  const db = new DatabaseSync(dbPath);
  assert.equal(db.prepare("SELECT Balance FROM Customers WHERE Account = ?").get(account).Balance, 1050);
  assert.equal(db.prepare("SELECT Balance FROM Customers WHERE Account = ?").get(recipient.body.account).Balance, 150);
  db.close();
});

test("rejects duplicate accounts and malformed input with useful status codes", async () => {
  const duplicate = await request("/api/accounts", {
    method: "POST",
    auth: false,
    body: {
      name: "Ada Lovelace",
      username: "ada-test",
      password: "longpassword",
      mobile: "1234567890",
      initialBalance: 0,
    },
  });
  assert.equal(duplicate.status, 409);

  const malformed = await request("/api/deposits", {
    method: "POST",
    body: { amount: -1 },
  });
  assert.equal(malformed.status, 400);
});

test("migrates an older database and invalidates logged-out tokens", async () => {
  const legacyPath = path.join(directory, "legacy.db");
  const legacyDb = new DatabaseSync(legacyPath);
  legacyDb.exec(`
    CREATE TABLE Customers(
      Id INTEGER PRIMARY KEY AUTOINCREMENT,
      Username TEXT UNIQUE NOT NULL,
      Password TEXT NOT NULL,
      Name TEXT NOT NULL,
      Mobile TEXT NOT NULL,
      Account INTEGER UNIQUE NOT NULL,
      Pin INTEGER,
      Balance INTEGER NOT NULL DEFAULT 0 CHECK(Balance >= 0)
    );
    CREATE TABLE Transactions(
      TransactionId INTEGER PRIMARY KEY AUTOINCREMENT,
      FromAccount INTEGER,
      ToAccount INTEGER,
      AmountTransferred INTEGER NOT NULL CHECK(AmountTransferred > 0),
      DateAndTime TEXT NOT NULL
    );
  `);
  legacyDb.close();

  const legacyServer = createBankServer({ dbPath: legacyPath, logger: { error() {} } });
  await new Promise((resolve) => legacyServer.listen(0, "127.0.0.1", resolve));
  const health = await fetch(`http://127.0.0.1:${legacyServer.address().port}/api/health`);
  assert.equal(health.status, 200);
  await new Promise((resolve) => legacyServer.close(resolve));

  const migratedDb = new DatabaseSync(legacyPath);
  assert.ok(migratedDb.prepare("PRAGMA table_info(Transactions)").all().some(({ name }) => name === "Type"));
  migratedDb.close();

  assert.deepEqual(await request("/api/auth/logout", { method: "POST" }), {
    status: 200,
    body: { message: "Logged out." },
  });
  assert.equal((await request("/api/me")).status, 401);
});
