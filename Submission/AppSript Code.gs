// Function Main Call calls the pdf generation and send email functions 
function maincall(a=['V1','V2','V3']) {
  for (var v of a) {
    var pdffile = exportSelectedRangeAsPDF(v);
    send_email(pdffile);
  }
}

// Export range as PDF
function exportSelectedRangeAsPDF(v) {
  // Logger.log(v);
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(v);
  var range = sheet.getRange('A1:H20'); // Change this to your desired range

  // Get the range details and generate PDF Blob
  var rangeA1Notation = range.getA1Notation();
  var sheetId = sheet.getSheetId();
  var spreadsheetId = SpreadsheetApp.getActiveSpreadsheet().getId();
  var url = 'https://docs.google.com/spreadsheets/d/' + spreadsheetId + '/export?exportFormat=pdf&format=pdf' +
            '&gid=' + sheetId + '&range=' + rangeA1Notation +
            '&size=A4' + // Paper size
            '&portrait=false' + // Orientation
            '&fitw=true' + // Fit to width
            '&sheetnames=false&printtitle=false&pagenumbers=false' + // Optional settings
            '&gridlines=false' + // Hide gridlines
            '&fzr=true'; // Do not repeat frozen rows
            '&top_margin=0.10' + // Top margin
            '&bottom_margin=0.10' + // Bottom margin
            '&left_margin=0.15' + // Left margin
            '&right_margin=0.15'; // Right margin

  var token = ScriptApp.getOAuthToken();
  var response = UrlFetchApp.fetch(url, {
    headers: {
      'Authorization': 'Bearer ' + token
    }
  });
  result =[response,v];
  return result
}

// Send Email of the pdf
function send_email(a) {  // Send the PDF via Gmail
  var response = a[0];
  var v = a[1];
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var emailAddress = ss.getRangeByName("email").getValue(); // Change this to the recipient's email address
  var location = ss.getRangeByName("location").getValue().toUpperCase(); 
  var from_date = ss.getRangeByName("from").getValue();
  var to_date = ss.getRangeByName("to").getValue(); 
  var from_formattedDate = Utilities.formatDate(from_date, Session.getScriptTimeZone(), "dd-MMM-yyyy");
  var to_formattedDate = Utilities.formatDate(to_date, Session.getScriptTimeZone(), "dd-MMM-yyyy");
  var subject = 'TripTailor AI : '+location+' '+v+' | '+from_formattedDate+' to '+to_formattedDate;
  var body = 'Greetings! \n\nHere is your customised AI generated Itinerary with location, timing and map links for your easy navigation. \n\nPrepared by Team KAVA. \nShare TripTailor with your friends :)';

  var token = ScriptApp.getOAuthToken();
  var pdfBlob = response.getBlob().setName(subject+'.pdf');

  MailApp.sendEmail(emailAddress, subject, body, {
    attachments: [pdfBlob]
  });
}

// Deployed as Webapp to call the Appscript
function process_(method, { parameter, postData }) {
  const lock = LockService.getScriptLock();
  if (lock.tryLock(350000)) {
    try {
      const { functionName } = parameter;
      let response = "No function.";
      if (functionName && !["doGet", "doPost"].includes(functionName)) {
        let args;
        if (method == "get") {
          const { arguments } = parameter;
          if (arguments) {
            args = JSON.parse(arguments);
          }
        } else if (method == "post" && postData) {
          const { contents } = postData;
          if (contents) {
            args = JSON.parse(contents);
          }
        }
        const res = this[functionName](args);
        response = typeof res == "object" ? JSON.stringify(res) : res;
      }
      return ContentService.createTextOutput(response);
    } catch ({ stack }) {
      return ContentService.createTextOutput(stack);
    } finally {
      lock.releaseLock();
    }
  } else {
    return ContentService.createTextOutput(Timeout);
  }
}

const doGet = (e) => process_("get", e);
const doPost = (e) => process_("post", e);

// This function is used for retrieving the Web Apps URL.
function getUrl() {
  console.log(ScriptApp.getService().getUrl());
}

