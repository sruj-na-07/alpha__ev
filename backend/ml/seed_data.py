"""
Seed training dataset for AlphaEV aspect-based sentiment and polarity classification.
Covers all 10 EV charging-station aspects with positive and negative polarities (20 classes).
"""

SEED_DATA = [
    # 1. Pricing
    ("The charging price is affordable and reasonable compared to other stations.", ["pricing:pos"]),
    ("Very good value for money with transparent charging tariffs.", ["pricing:pos"]),
    ("The rates are clearly displayed before starting a charging session.", ["pricing:pos"]),
    ("Affordable charging costs make this station a good choice for daily use.", ["pricing:pos"]),

    ("Charging is too expensive compared to nearby charging stations.", ["pricing:neg"]),
    ("The app shows one price but charges a higher amount after the session.", ["pricing:neg"]),
    ("Hidden fees make the total charging cost unnecessarily high.", ["pricing:neg"]),
    ("The per-unit charging rate is unreasonable and needs to be reduced.", ["pricing:neg"]),

    # 2. Payment Issues
    ("UPI payment worked instantly and the charging session started without problems.", ["payment_issues:pos"]),
    ("The payment process is smooth and supports multiple payment methods.", ["payment_issues:pos"]),
    ("Payment confirmation arrived immediately and the receipt was accurate.", ["payment_issues:pos"]),
    ("The wallet balance and transaction history are updated correctly.", ["payment_issues:pos"]),

    ("My UPI payment failed but the money was deducted from my bank account.", ["payment_issues:neg"]),
    ("The app deducted money twice for the same charging session.", ["payment_issues:neg"]),
    ("I have not received my refund even after several days.", ["payment_issues:neg"]),
    ("Payment errors prevent me from starting a charging session.", ["payment_issues:neg"]),

    # 3. Charging Speed
    ("The charger delivers fast charging and fills the battery quickly.", ["charging_speed:pos"]),
    ("Charging speed is excellent and the power output remains consistent.", ["charging_speed:pos"]),
    ("My vehicle charged quickly without unexpected speed drops.", ["charging_speed:pos"]),
    ("The fast charger reduced my charging time considerably.", ["charging_speed:pos"]),

    ("Charging is extremely slow even when the charger is rated for fast charging.", ["charging_speed:neg"]),
    ("The charging speed keeps dropping and takes too long to charge the vehicle.", ["charging_speed:neg"]),
    ("The charger delivers much less power than expected.", ["charging_speed:neg"]),
    ("A short charging session takes far longer than it should.", ["charging_speed:neg"]),

    # 4. Reliability
    ("The charging station works consistently and every session starts successfully.", ["reliability:pos"]),
    ("The charger has been dependable during all my visits.", ["reliability:pos"]),
    ("The station operates reliably without unexpected interruptions.", ["reliability:pos"]),
    ("Charging completed successfully without technical errors.", ["reliability:pos"]),

    ("The charger repeatedly stops working in the middle of a session.", ["reliability:neg"]),
    ("The charging station frequently shows errors and fails to start charging.", ["reliability:neg"]),
    ("The connector disconnects repeatedly and interrupts charging.", ["reliability:neg"]),
    ("This station is unreliable because it frequently goes out of service.", ["reliability:neg"]),

    # 5. Waiting Time
    ("There was no queue and I could start charging immediately.", ["waiting_time:pos"]),
    ("The waiting time was minimal even during a busy period.", ["waiting_time:pos"]),
    ("I was able to access the charger without any delay.", ["waiting_time:pos"]),
    ("Quick access to the charging point saved me a lot of time.", ["waiting_time:pos"]),

    ("I waited for more than an hour before a charger became available.", ["waiting_time:neg"]),
    ("Long queues at this station waste too much time.", ["waiting_time:neg"]),
    ("Other vehicles were occupying the chargers and the wait was frustrating.", ["waiting_time:neg"]),
    ("The delay before starting my charging session was unacceptable.", ["waiting_time:neg"]),

    # 6. App Usability
    ("The app is easy to use and finding charging stations is straightforward.", ["app_usability:pos"]),
    ("The interface is simple and starting a charging session is convenient.", ["app_usability:pos"]),
    ("The app clearly displays charging status and session details.", ["app_usability:pos"]),
    ("The app runs smoothly and makes managing charging sessions easy.", ["app_usability:pos"]),

    ("The app keeps crashing whenever I try to start charging.", ["app_usability:neg"]),
    ("The interface is confusing and it is difficult to find basic options.", ["app_usability:neg"]),
    ("The app shows incorrect charging status and does not update properly.", ["app_usability:neg"]),
    ("Login problems and app errors make the charging process frustrating.", ["app_usability:neg"]),

    # 7. Availability
    ("Chargers are available whenever I visit this station.", ["availability:pos"]),
    ("There are enough operational charging points for customers.", ["availability:pos"]),
    ("The station has multiple working chargers and is easy to access.", ["availability:pos"]),
    ("I could find an available charging point without any difficulty.", ["availability:pos"]),

    ("All chargers were occupied when I arrived.", ["availability:neg"]),
    ("The station is listed in the app but the chargers are out of service.", ["availability:neg"]),
    ("There are too few charging points available at this location.", ["availability:neg"]),
    ("The app shows a charger as available even though it is not operational.", ["availability:neg"]),

    # 8. Location Convenience
    ("The charging station is conveniently located near the main road.", ["location_convenience:pos"]),
    ("The station is easy to reach and close to useful shops.", ["location_convenience:pos"]),
    ("The location is convenient for charging during my daily commute.", ["location_convenience:pos"]),
    ("Clear directions make the charging station easy to find.", ["location_convenience:pos"]),

    ("The charging station is far away from the main road and difficult to reach.", ["location_convenience:neg"]),
    ("The location is inconvenient and requires a long detour.", ["location_convenience:neg"]),
    ("Poor directions make it difficult to find the charging point.", ["location_convenience:neg"]),
    ("There are no convenient charging locations in this area.", ["location_convenience:neg"]),

    # 9. Improvement Suggestion
    ("Please add more charging points to reduce congestion.", ["improvement_suggestion:pos"]),
    ("The service could be improved by providing more payment options.", ["improvement_suggestion:pos"]),
    ("I suggest adding live charger availability updates to the app.", ["improvement_suggestion:pos"]),
    ("Please provide better seating and shelter while customers charge.", ["improvement_suggestion:pos"]),

    ("The company should reduce charging prices and remove hidden fees.", ["improvement_suggestion:neg"]),
    ("Please fix the frequent payment failures and refund delays.", ["improvement_suggestion:neg"]),
    ("They need to improve charger maintenance and reliability.", ["improvement_suggestion:neg"]),
    ("The app needs a better interface and more accurate station information.", ["improvement_suggestion:neg"]),

    # 10. Overall Experience
    ("Overall, I had an excellent experience using this charging station.", ["overall_experience:pos"]),
    ("The charging service was convenient and I am satisfied with my visit.", ["overall_experience:pos"]),
    ("Everything went smoothly and I would recommend this station to others.", ["overall_experience:pos"]),
    ("A pleasant charging experience with helpful facilities and smooth service.", ["overall_experience:pos"]),

    ("Overall, this was a frustrating and disappointing charging experience.", ["overall_experience:neg"]),
    ("I am dissatisfied with the service and would avoid this station.", ["overall_experience:neg"]),
    ("The entire charging experience was inconvenient and poorly managed.", ["overall_experience:neg"]),
    ("I would not recommend this charging network because of my experience.", ["overall_experience:neg"]),
        # Customer Support - Positive
    ("Customer support responded quickly and resolved my charging issue.", ["customer_support:pos"]),
    ("The support team was helpful when I faced a problem starting my charging session.", ["customer_support:pos"]),
    ("Customer care provided clear instructions and helped me complete the payment.", ["customer_support:pos"]),
    ("The support team followed up on my complaint and resolved it promptly.", ["customer_support:pos"]),

    #11. Customer Support - Negative
    ("Customer support never responded to my complaint about the charging station.", ["customer_support:neg"]),
    ("I contacted customer care several times but nobody resolved my issue.", ["customer_support:neg"]),
    ("The support team was unhelpful when my payment was deducted but charging did not start.", ["customer_support:neg"]),
    ("My complaint about the faulty charger remains unresolved despite repeated calls.", ["customer_support:neg"]),
]

ASPECT_DISPLAY_NAMES = {
    "pricing": "Pricing",
    "payment_issues": "Payment Issues",
    "charging_speed": "Charging Speed",
    "reliability": "Reliability",
    "waiting_time": "Waiting Time",
    "app_usability": "App Usability",
    "availability": "Availability",
    "location_convenience": "Location Convenience",
    "improvement_suggestion": "Improvement Suggestion",
    "overall_experience": "Overall Experience",
    "customer_support": "Customer Support",
}

ALL_LABELS = [
    f"{aspect}:{polarity}"
    for aspect in ASPECT_DISPLAY_NAMES.keys()
    for polarity in ("pos", "neg")
]