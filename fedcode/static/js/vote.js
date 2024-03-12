function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
function sendVote(url, submit_button, current_value) {
   $.ajax({
      type: "PUT",
      url: url,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      data: JSON.stringify({"vote-type": submit_button.attr("name")}),
      dataType: "json",
      success: (data) => {
          let obj_id = submit_button.attr("value")
          let vote_value = document.getElementsByName(obj_id)[0]
          let current_value = vote_value.innerHTML
          if (data['vote-type'] === "vote-up"){
              vote_value.innerHTML = parseInt(parseFloat(current_value)) + 1;
          }

          if (data['vote-type'] === "vote-down")  {
              vote_value.innerHTML = parseInt(parseFloat(current_value)) - 1;
          }
      },
      error: (error) => {
        console.log(error);
      }
   });
}
$(document).ready(function () {
    $("form[name='vote-notes']").submit(function (event) {
      event.preventDefault();
      let submit_button = $(event.originalEvent.submitter);
      if ((submit_button.attr("name") === "vote-up") ||
          (submit_button.attr("name") === "vote-down")) {
          let note_id = submit_button.attr("value")
          let url = "/notes/"+ note_id +"/votes/"
          let current_value = $( "#" + note_id).text();
          sendVote(url, submit_button, current_value);
      }
  });

    $("form[name='vote-review']").submit(function (event) {
      event.preventDefault();
      let submit_button = $(event.originalEvent.submitter);
      if ((submit_button.attr("name") === "vote-up") ||
          (submit_button.attr("name") === "vote-down")) {
          let review_id = submit_button.attr("value")
          let url = "/reviews/"+ review_id  + "/votes/"
          let current_value = $("#votes-review-value").text();
          sendVote(url, submit_button , current_value);
       }
    });

});