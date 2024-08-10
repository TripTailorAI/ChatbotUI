import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
import google.auth.transport.requests
import pygsheets
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))

@st.cache_data(ttl=3600)
def create_itinerary_pdf(itinerary, set_number, itinerary_number, mode_of_transport):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    header_color = colors.HexColor('#1C4E80')  # Deep blue
    row_color1 = colors.HexColor('#F0F7FF')    # Very light blue
    row_color2 = colors.HexColor('#FFFFFF')    # White
    title_color = colors.HexColor('#0A2C4E')   # Darker blue for titles
    border_color = colors.HexColor('#7AA5C9')  # Light blue for borders

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=1, fontName='DejaVuSans', textColor=title_color))
    styles.add(ParagraphStyle(name='Small', fontSize=8, fontName='DejaVuSans'))
    styles.add(ParagraphStyle(name='Thank You', fontSize=14, alignment=1, spaceAfter=12, fontName='DejaVuSans', textColor=title_color))
    styles.add(ParagraphStyle(name='Info', fontSize=10, alignment=1, spaceAfter=12, fontName='DejaVuSans', textColor=colors.HexColor('#1C4E80')))
    # Add thank you message
    elements.append(Paragraph("Thank you for using TripTailorAI!", styles['Thank You']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Itinerary {itinerary_number} from Set {set_number}", styles['Heading1']))
    elements.append(Spacer(1, 12))

    for day in itinerary:
        elements.append(Paragraph(f"Date: {day['date']}", styles['Heading2']))
        elements.append(Paragraph(f"Weather forecast: {day['weather']}", styles['Normal']))
        elements.append(Spacer(1, 12))

        data = [['Time', 'Activity', 'Place', 'Address', 'Opening Hours', 'Travel Time']]
        for i, activity in enumerate(day['activities']):
            row = [
                Paragraph(activity['time'], styles['Small']),
                Paragraph(activity['activity'], styles['Small']),
                Paragraph(activity['place']['name'], styles['Small']),
                Paragraph(activity['place']['formatted_address'], styles['Small']),
                Paragraph(activity.get('opening_hours', 'N/A'), styles['Small']),
                Paragraph(activity.get('duration_to_next', 'N/A') if i < len(day['activities']) - 1 else 'N/A', styles['Small'])
            ]
            data.append(row)

        table = Table(data, colWidths=[0.5*inch, 1.8*inch, 1.5*inch, 2.5*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), header_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), row_color1),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 1, border_color),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [row_color1, row_color2])
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

    info_text = "Did you know that if you press the 'Send all itineraries' button, you'll get all of your itineraries in your email?"
    elements.append(Paragraph(info_text, styles['Info']))

    doc.build(elements)
    buffer.seek(0)
    return buffer

@st.cache_data(ttl=3600)
def display_itinerary(itinerary, set_number, itinerary_number, mode_of_transport):
    itinerary_message = ""
    day_data = []
    for day in itinerary:
        date = day['date']
        weather = day['weather']
        itinerary_message += f"**Date:** {date}\n\n"
        itinerary_message += f"**Weather forecast:** {weather}\n\n"
        for i, activity in enumerate(day['activities']):
            time = activity['time']
            activity_name = activity['activity']
            place_name = activity['place']['name']
            address = activity['place']['formatted_address']
            opening_hours = activity.get('opening_hours', 'N/A')
            
            itinerary_message += f"- {time}: {activity_name} at [{place_name}]({activity['place'].get('url', '#')})\n"
            itinerary_message += f"  - Address: {address}\n"
            itinerary_message += f"  - Opening Hours: {opening_hours}\n"
            if i < len(day['activities']) - 1:
                duration_value = activity.get('duration_to_next_value', float('inf'))
                duration_text = activity.get('duration_to_next', 'N/A')
                if duration_value <= 1800:  # 30 minutes or less
                    color = 'green'
                elif duration_value <= 3600:  # 1 hour or less
                    color = 'yellow'
                else:
                    color = 'red'
                itinerary_message += f"  - :clock3: Travel time to next location ({mode_of_transport[:-8]}): <font color='{color}'>{duration_text}</font>\n"
            
            day_data.append([date, weather, time, activity_name, place_name, address, opening_hours])
        
        itinerary_message += "---\n\n"
    
    st.markdown(itinerary_message, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"Export Itinerary {itinerary_number} as PDF 📄", key=f"export_pdf_{set_number}_{itinerary_number}_{id(itinerary)}"):
            pdf_buffer = create_itinerary_pdf(itinerary, set_number, itinerary_number, mode_of_transport)
            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name=f"itinerary_{set_number}_{itinerary_number}.pdf",
                mime="application/pdf"
            )
            st.success(f"Itinerary {itinerary_number} from Set {set_number} exported as PDF.")
    with col2:
        if st.button(f"Send Itinerary {itinerary_number} via Email 📧", key=f"send_email_{set_number}_{itinerary_number}_{id(itinerary)}"):
            send_to_gsheets()
            send_email(['V'+str(itinerary_number)])
            st.success(f"Itinerary {itinerary_number} from Set {set_number} sent via email.")
    
    return day_data

@st.cache_data(ttl=3600)
def generate_df(itinerary_set):
    itinerary_data = []
    columns = ['itinerary_version', 'date', 'weather', 'time', 'activity', 'place', 'MapsLink', 'Address', 'Hours']
    
    day_itineraries = itinerary_set.get('day', [])
    night_itineraries = itinerary_set.get('night', [])
    
    for i, itinerary in enumerate(day_itineraries, 1):
        for day in itinerary:
            for activity in day['activities']:
                itinerary_data.append([
                    f"{i} (Day)",
                    day['date'],
                    day['weather'],
                    activity['time'],
                    activity['activity'],
                    activity['place']['name'],
                    activity['place']['url'],
                    activity['place']['formatted_address'],
                    activity['opening_hours']
                ])
    
    if night_itineraries:
        for i, itinerary in enumerate(night_itineraries, 1):
            for day in itinerary:
                for activity in day['activities']:
                    itinerary_data.append([
                        f"{i} (Night)",
                        day['date'],
                        day['weather'],
                        activity['time'],
                        activity['activity'],
                        activity['place']['name'],
                        activity['place']['url'],
                        activity['place']['formatted_address'],
                        activity['opening_hours']
                    ])
    
    df = pd.DataFrame(itinerary_data, columns=columns)
    return df

@st.cache_data(ttl=3600)
def send_to_gsheets(email_address,destination,start_date,end_date):
    if st.session_state.all_generated_itineraries:
        most_recent_set = st.session_state.all_generated_itineraries[-1]
        df = generate_df(most_recent_set)
        
        service_account_info = st.secrets["gcp_service_account"]
        
        # Create credentials object
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        
        # Authorize with pygsheets using the credentials
        gc = pygsheets.authorize(custom_credentials=credentials)
        
        # Rest of your function remains the same
        sheet_id = '1Mw_kkGf8Z5qN2RGhOzIM04zEN30cZIznrOfjWPwNluc'
        worksheet_name = 'Base_Day'
        sh = gc.open_by_key(sheet_id)
        wks = sh.worksheet_by_title(worksheet_name)  # Select the first sheet
        start_cell = 'C2'
        end_cell = 'K500'
        wks.clear(start=start_cell, end=end_cell)
        wks.set_dataframe(df, (1, 3))
        worksheet_name = 'Master'
        wks = sh.worksheet_by_title(worksheet_name)  # Select the first sheet
        wks.update_value("B1", email_address)
        wks.update_value("B2", destination)
        wks.update_value("B3", start_date.strftime("%Y-%m-%d"))
        wks.update_value("B4", end_date.strftime("%Y-%m-%d"))
        return True
    else:
        return False


def getAccessToken():
    service_account_email = st.secrets["gcp_service_email"]
    # SERVICE_ACCOUNT_FILE = "sheets-drive-api-1-7785bd353bca.json" # Please set your value.
    # creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/drive.readonly"])
    creds = Credentials.from_service_account_info(service_account_email,scopes=["https://www.googleapis.com/auth/drive.readonly"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token
    
@st.cache_data(ttl=3600)
def send_email(arguments):
    functionName = "maincall"
    webApps_url = 'https://script.google.com/macros/s/AKfycbxL1kUB-TaP6oFEpZgFzAUhOvtHm6bnDgaPpcNZ-xA/dev'
    access_token = getAccessToken()
    url = f'{webApps_url}?functionName={functionName}'
    res = requests.post(url, json.dumps(arguments), headers={"Authorization": "Bearer " + access_token})
    print(res.text)