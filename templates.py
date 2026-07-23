"""
Slack message templates for EMEA All Hands communications.
Each function returns a plain-text message with event details filled in.
"""


def contributor_message(
    presentation_title: str,
    presentation_link: str,
    support_contacts: str = "Rolando Angelini or Wojtek Szambelan",
) -> str:
    if presentation_title and presentation_link:
        pres_ref = f"<{presentation_link}|{presentation_title}>"
    elif presentation_link:
        pres_ref = presentation_link
    elif presentation_title:
        pres_ref = presentation_title
    else:
        pres_ref = "[presentation link]"

    contacts = support_contacts.replace(",", " or", 1) if "," in support_contacts else support_contacts

    return (
        f"Hi all,\n"
        f"Thank you for being a contributor to our next EMEA All Hands! "
        f"We're delighted you'll be presenting.\n"
        f"You'll have about 10 minutes to present your topic. "
        f"Please ensure your slides are finalized and ready by the date of the event.\n"
        f"Here is the presentation you'll need to work on: {pres_ref}\n"
        f"If you have any questions, feel free to contact {contacts}.\n"
        f"Thanks again for your contribution\u2014we're looking forward to your presentation!"
    )


def contributor_pre_event_reminder() -> str:
    return (
        "Hi all 👋\n"
        "Just a quick reminder that our next EMEA All Hands is happening next Monday.\n"
        "If you haven't already, please take a moment to review and update your slides "
        "to ensure they're finalized and ready for the presentation.\n"
        "If you have any questions or need support, please reach out to Rolando, Wojtek, "
        "Klaudyna, or me.\n"
        "Thank you all for your contributions—we're looking forward to another great session!"
    )


def pre_event_reminder(
    event_date: str,
    event_time: str = "12pm",
    uk_time: str = "11am",
    zoom_link: str = "",
) -> str:
    zoom = zoom_link or "[ZOOM LINK]"
    return (
        f"Happy Monday Affirmers! \U0001f389\n\n"
        f"Just a reminder to join today's EMEA All Hands at {event_time} "
        f"({uk_time} UK time). Looking forward to seeing you all there! {zoom}"
    )


def post_event_followup(
    recording_link: str,
    recording_passcode: str,
    survey_link: str,
) -> str:
    rec = recording_link or "[recording link]"
    passcode = recording_passcode or "[passcode]"
    survey = survey_link or "[survey link]"
    return (
        f"Hi all,\n"
        f"Thank you for attending Monday's EMEA All Hands, and a special thanks "
        f"to all the presenters! \U0001f389\n"
        f"Recording available here {rec} (Passcode: {passcode})\n"
        f"We'd love to hear your feedback to help us improve these sessions. "
        f"Could you take a quick moment (less than 2 minutes!) to complete this "
        f"brief survey? Your input is invaluable.\n"
        f"{survey}\n"
        f"Thanks very much!"
    )
