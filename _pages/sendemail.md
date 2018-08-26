<form>
<label>Email Address</label>
<input type="email" id ="inputEmail" class="form-control" placeholder="Email Address" required autofocus>
<button class="btn btn-lg btn-primary btn-block" type="submit"> Subscribe!</button>
</form>


<script src="https://www.gstatic.com/firebasejs/5.4.1/firebase.js"></script>
<script>
  // Initialize Firebase
  var config = {
    apiKey: "AIzaSyDtHgvPy_AMQ6hj2cLNLSnlo8SxmAer5BU",
    authDomain: "ethionlp.firebaseapp.com",
    databaseURL: "https://ethionlp.firebaseio.com",
    projectId: "ethionlp",
    storageBucket: "ethionlp.appspot.com",
    messagingSenderId: "922706194013"
  };
  firebase.initializeApp(config);

  function saveToFirebase(email) {
    var emailObject = {
        email: email
    };

    firebase.database().ref('subscription-entries').push().set(emailObject)
        .then(function(snapshot) {
            success(); // some success method
        }, function(error) {
            console.log('error' + error);
            error(); // some error method
        });
}
</script>