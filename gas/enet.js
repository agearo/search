function doPost(e) {
  var data = JSON.parse(e.postData.contents);
  var subject = data.subject;
  var body = data.body;
  GmailApp.sendEmail("your_email@gmail.com", subject, body);
  return ContentService.createTextOutput("Email sent");
}
