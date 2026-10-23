const express = require("express");
const http = require("http");
const fs = require("fs");
const { Server } = require("socket.io");

const app = express();
const server = http.createServer(app);
const io = new Server(server);
const LOG = __dirname + "/alerts.log";

app.use(express.json());
app.use(express.static(__dirname + "/public"));

app.post("/stats", (req, res) => {
  io.emit("stats", req.body);
  res.sendStatus(200);
});

app.post("/alert", (req, res) => {
  const alert = req.body;
  if (!alert.type || !alert.src || !alert.severity) return res.sendStatus(400);
  alert.date = new Date().toISOString().slice(0, 10);
  fs.appendFileSync(LOG, JSON.stringify(alert) + "\n");
  io.emit("alert", alert);
  res.sendStatus(200);
});

app.get("/api/alerts", (req, res) => {
  const lines = fs.existsSync(LOG) ? fs.readFileSync(LOG, "utf8").trim().split("\n").filter(Boolean) : [];
  res.json(lines.slice(-100).map(line => JSON.parse(line)));
});

server.listen(3000, () => console.log("Dashboard running at http://localhost:3000"));
