const express = require('express');
const app = express();

// This is an example of the configuration concept
const dotenv = require("dotenv");
dotenv.config();

//models
const TodoTask = require("./models/TodoTask");

//connection to db
// This is clearly the database integration concept, since MongoDB is innately a database framework
const mongoose = require("mongoose");
mongoose.connect(process.env.DB_CONNECT, { useNewUrlParser: true }, () => {
console.log("Connected to db!");

// This is an example of the listening concept
app.listen(4000, () => console.log("Server Up and running"));
});

app.use("/static", express.static("public"));

app.set("view engine", "ejs");

// By supplying the first argument, "/" and the type of request, "Get", this is an example of the routing concept
// Node.js takes any GET requests to the "/" URL and routes them to this method
// GET METHOD
app.get("/", (req, res) => {
    TodoTask.find({}, (err, tasks) => {
        res.render("todo.ejs", {
            todoTasks: tasks
        });
    });
});

app.use(express.urlencoded({ extended: true }));

//POST METHOD
app.post('/', async (req, res) => {
    const todoTask = new TodoTask({
        content: req.body.content
    });
    try {
        await todoTask.save();
        res.redirect("/");
    } catch (err) {
        res.redirect("/");
    }
});

//UPDATE
app.route("/edit/:id")
    .get((req, res) => {
        const id = req.params.id;
        TodoTask.find({}, (err, tasks) => {
            res.render("todoEdit.ejs", {
                todoTasks: tasks,
                idTask: id
            });
        });
    })
    .post((req, res) => {
        const id = req.params.id;
        TodoTask.findByIdAndUpdate(id, {
            content: req.body.content
        }, err => {
            if (err) return res.send(500, err);
            res.redirect("/");
        });
    });

//DELETE
app.route("/remove/:id").get((req, res) => {
    const id = req.params.id;
    TodoTask.findByIdAndRemove(id, err => {
        if (err) return res.send(500, err);
        res.redirect("/");
    });
});