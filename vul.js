// handler.js
const { Sequelize, DataTypes } = require("sequelize");

// Reuse connection across invocations (Lambda best practice)
const sequelize = new Sequelize({
  dialect: "sqlite",          // swap to 'mysql' | 'postgres' in real apps
  storage: "database.sqlite", // demo only
  logging: false
});

const User = sequelize.define("User", {
  name: { type: DataTypes.STRING },
  email: { type: DataTypes.STRING }
});

async function initDB() {
  await sequelize.sync({ force: true });
  await User.bulkCreate([
    { name: "Alice", email: "alice@example.com" },
    { name: "Bob",   email: "bob@example.com"   }
  ]);
}
const dbReady = initDB();

// ❌ Vulnerable: tainted $EVENT -> raw SQL concatenation
exports.vulnerable = async (event) => {
  await dbReady;
  const id = (event.queryStringParameters || {}).id ?? "";

  try {
    const rows = await sequelize.query(
      `SELECT * FROM Users WHERE id = ${id}`, // SQL injection risk
      { type: sequelize.QueryTypes.SELECT }
    );
    return { statusCode: 200, body: JSON.stringify(rows) };
  } catch (err) {
    return { statusCode: 500, body: JSON.stringify({ error: err.message }) };
  }
};

// ✅ Secure: parameterized query using replacements
exports.secure = async (event) => {
  await dbReady;
  const id = (event.queryStringParameters || {}).id ?? "";

  try {
    const rows = await sequelize.query(
      "SELECT * FROM Users WHERE id = :id",
      {
        replacements: { id },                 // safely escaped
        type: sequelize.QueryTypes.SELECT
      }
    );
    return { statusCode: 200, body: JSON.stringify(rows) };
  } catch (err) {
    return { statusCode: 500, body: JSON.stringify({ error: err.message }) };
  }
};

// ✅ Bonus: secure via model APIs (also parameterized internally)
exports.secureModelApi = async (event) => {
  await dbReady;
  const id = (event.queryStringParameters || {}).id ?? "";

  try {
    const user = await User.findOne({ where: { id } }); // safe
    return { statusCode: 200, body: JSON.stringify(user) };
  } catch (err) {
    return { statusCode: 500, body: JSON.stringify({ error: err.message }) };
  }
};
