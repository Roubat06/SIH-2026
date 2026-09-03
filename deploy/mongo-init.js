// Runs only when MongoDB initializes a new data directory.
const appDb = db.getSiblingDB("bitcoin_sentinel");

if (!process.env.MONGO_APP_PASSWORD) {
  throw new Error("MONGO_APP_PASSWORD is required");
}

appDb.createUser({
  user: "sentinel_app",
  pwd: process.env.MONGO_APP_PASSWORD,
  roles: [{ role: "readWrite", db: "bitcoin_sentinel" }],
});
