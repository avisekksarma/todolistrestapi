### Todolist RESTful API

This is a RESTful API made in flask as backend and postgres as database.

##### How to use the API?

The Base URL is : http://127.0.0.1:5000

Firstly you need to make a POST request to : /api/makeapp
In JavaScript it would be something like:

##### Format
```
fetch(BASEURL + '/api/makeapp', {
  method: 'POST',
  headers: {
      'Content-type':'application/json'
  },
  body: JSON.stringify({
      app_name : 'your_unique_app_name'
  })
})
.then(response => response.json())
.then(result => {
    // Print result
    console.log(result);
    // do sth with result
});
```
The name of the app can be a string i.e even with spaces and special characters but you need to remember it. It is not like your password so you may share it to others if you like but we recommend not doing so.

If the app name is already taken then the result object will have status code = 400 else if successful then result.status_code == 200 check could be done. 

Also, In every result the message key will give the message about the response. i.e result.message can provide information of the response by server.

Now, after taking the app name you are good to go.
The endpoints are:

1. POST: /api/register 
    - this route is used to register a user to your todo app.
    - the body in the above format needs to have username, email, password, app_name where app_name is your unique app name. All the values are strings.
    Example:
        ```
        body: JSON.stringify({
            username : 'bob',
            email: 'bob@gmail.com',
            password: '12345'
            app_name : 'your_unique_app_name'
        })
        ```
    - each user in your todo app must have a unique username and email 
    - for duplicate username : result will be 
2. 
