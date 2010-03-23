
function checkout(bookKey) {
        $.ajax({
                type: "POST",
                data: "key="+bookKey,
                url: "/book/checkout",
                success: function(xml) {
                  //$(".checkout").fadeOut("slow");
                  //$(".checkout").removeClass("checkout");
                } // success function
              }); // .ajax
}
      
function checkin(bookKey) {
        $.ajax({
                type: "POST",
                data: "key="+bookKey,
                url: "/book/checkin",
                success: function(xml) {
                  //$(".checkout").fadeOut("slow");
                  //$(".checkout").removeClass("checkout");
                } // success function
              }); // .ajax
}

function redirectUser(userKey) {
    window.location = "/user?user="+userKey;
}
      
function redirectBook(bookKey) {
    window.location = "/book?book="+bookKey;
}
