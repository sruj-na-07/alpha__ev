"""
Seed training dataset for AlphaEV aspect-based sentiment and polarity classification.
Covers all 11 aspects with both positive and negative polarities (22 classes).
"""

SEED_DATA = [
    # Range & Battery - Positive
    ("The battery range easily exceeds 300 miles on the highway, very minimal degradation after 20k miles.", ["range_battery:pos"]),
    ("Great efficiency and battery life! The EPA estimate is conservative, I consistently get 320 miles.", ["range_battery:pos"]),
    ("Battery health has remained at 98% even with daily DC fast charging, outstanding battery technology.", ["range_battery:pos"]),
    ("Outstanding real-world range even in chilly winter conditions, the heat pump keeps the battery warm.", ["range_battery:pos"]),

    # Range & Battery - Negative
    ("Severe battery degradation after only one year, lost nearly 25% of maximum range capacity.", ["range_battery:neg"]),
    ("The winter range is horrific, drops by 45% as soon as temperatures hit freezing.", ["range_battery:neg"]),
    ("Phantom battery drain drains 10 miles of charge overnight while parked in the driveway.", ["range_battery:neg"]),
    ("Stated range is an absolute lie, barely getting 180 miles instead of advertised 300.", ["range_battery:neg"]),

    # Charging - Positive
    ("Charges from 10% to 80% in 18 minutes flat at 350kW CCS stations, super fast charging speed.", ["charging:pos"]),
    ("Tesla Supercharger network access has made road trips effortless and reliable with zero queue.", ["charging:pos"]),
    ("Seamless plug and charge experience, handles 250kW peak rate effortlessly without throttling.", ["charging:pos"]),
    ("Home Level 2 charging is fast and cost-effective, ready every morning.", ["charging:pos"]),

    # Charging - Negative
    ("Charging stations are broken half the time and the charge speed throttles below 40kW.", ["charging:neg"]),
    ("The CCS connector got stuck in the port and charging failed three times at Electrify America.", ["charging:neg"]),
    ("Painfully slow charging curve, takes over an hour to go from 20% to 80% on fast chargers.", ["charging:neg"]),
    ("Constant communication errors with public chargers, refused to initiate session.", ["charging:neg"]),

    # Performance - Positive
    ("Instant torque and mind-blowing acceleration, 0-60 in 3.1 seconds pushes you into the seat.", ["performance:pos"]),
    ("Incredible handling through corners, low center of gravity makes it feel glued to the road.", ["performance:pos"]),
    ("Regenerative braking is tuned perfectly for smooth true one-pedal driving in city traffic.", ["performance:pos"]),
    ("Effortless passing power on the highway and razor-sharp steering dynamics.", ["performance:pos"]),

    # Performance - Negative
    ("Mushy brake feel and alarming understeer when pushed in tight corners.", ["performance:neg"]),
    ("The regenerative braking feels jerky and cannot be adjusted, causes motion sickness.", ["performance:neg"]),
    ("Acceleration feels sluggish after 60 mph, lacks top-end highway passing punch.", ["performance:neg"]),
    ("Noticeable motor whining noise and heavy feeling around curves.", ["performance:neg"]),

    # Software & Infotainment - Positive
    ("The touchscreen is butter smooth and the navigation with EV route planning is flawless.", ["software_infotainment:pos"]),
    ("Regular OTA updates keep adding fantastic features, Apple CarPlay works wirelessly without hitch.", ["software_infotainment:pos"]),
    ("Intuitive user interface with snappy response and clear crisp graphics on the infotainment.", ["software_infotainment:pos"]),
    ("The companion phone app is lightning fast at waking the vehicle and setting climate controls.", ["software_infotainment:pos"]),

    # Software & Infotainment - Negative
    ("The infotainment screen freezes constantly and rebooted twice while driving on highway.", ["software_infotainment:neg"]),
    ("Software is full of annoying bugs, Bluetooth disconnects every 10 minutes and no CarPlay.", ["software_infotainment:neg"]),
    ("Laggy touch response and sluggish navigation system that cannot calculate accurate routes.", ["software_infotainment:neg"]),
    ("Terrible mobile app that always fails to connect to the vehicle remotely.", ["software_infotainment:neg"]),

    # Interior & Comfort - Positive
    ("Whisper quiet cabin at 75 mph with zero wind noise and exceptionally comfortable ergonomic seats.", ["interior_comfort:pos"]),
    ("The suspension absorbs potholes like a luxury limousine, very smooth ride quality.", ["interior_comfort:pos"]),
    ("Premium materials throughout the interior, supportive heated and ventilated seating.", ["interior_comfort:pos"]),
    ("Excellent dual-zone HVAC system and effective heated steering wheel for winter mornings.", ["interior_comfort:pos"]),

    # Interior & Comfort - Negative
    ("Cheap scratchy plastic all over the cabin, feels like a budget economy car on the inside.", ["interior_comfort:neg"]),
    ("Stiff and harsh suspension, every minor bump and expansion joint shakes the entire car.", ["interior_comfort:neg"]),
    ("Excessive road noise and tire roar penetrate the interior at highway speeds.", ["interior_comfort:neg"]),
    ("The front seats offer zero lumbar support and become painful after just an hour of driving.", ["interior_comfort:neg"]),

    # Build Quality - Positive
    ("Flawless paint finish and laser-tight panel gaps everywhere, rock solid build quality.", ["build_quality:pos"]),
    ("No squeaks, rattles, or loose trims even over rough gravel roads, exemplary fit and finish.", ["build_quality:pos"]),
    ("Doors close with a reassuring solid thud and weather seals are completely watertight.", ["build_quality:pos"]),
    ("Robust exterior hardware and paint that has resisted rock chips exceptionally well.", ["build_quality:pos"]),

    # Build Quality - Negative
    ("Disastrous panel gaps, misaligned trunk lid, and loose rubber seals around the windows.", ["build_quality:neg"]),
    ("Rattles and squeaks coming from the dashboard and B-pillar within the first 1,000 miles.", ["build_quality:neg"]),
    ("Thin peeling clear coat and orange peel paint defects straight from the factory.", ["build_quality:neg"]),
    ("Water leaks into the taillight housing every time it rains.", ["build_quality:neg"]),

    # Safety & Driver Assistance - Positive
    ("Adaptive cruise control and lane centering work seamlessly in heavy rush-hour traffic.", ["safety_driver_assist:pos"]),
    ("The blind spot cameras and 360-degree overhead parking view make maneuvering effortless.", ["safety_driver_assist:pos"]),
    ("Forward collision warning avoided a rear-end collision, five-star crash test security.", ["safety_driver_assist:pos"]),
    ("Highway driver assist steers smoothly without bouncing between lane markings.", ["safety_driver_assist:pos"]),

    # Safety & Driver Assistance - Negative
    ("Terrifying phantom braking on empty highway stretches while using driver assist.", ["safety_driver_assist:neg"]),
    ("Lane keep assist aggressively yanks the steering wheel towards concrete barriers.", ["safety_driver_assist:neg"]),
    ("Blind spot monitoring sensors frequently trigger false alarms in rain.", ["safety_driver_assist:neg"]),
    ("Driver monitoring camera is overly sensitive, constantly beeps even when looking forward.", ["safety_driver_assist:neg"]),

    # Price & Value - Positive
    ("Incredible value for money when factoring in the $7,500 federal EV tax credit.", ["price_value:pos"]),
    ("Total cost of ownership is tiny compared to gas, saved thousands on fuel and maintenance.", ["price_value:pos"]),
    ("Generous standard equipment package for the price point, undercuts competitors by $10k.", ["price_value:pos"]),
    ("Resale value has held remarkably well over two years of ownership.", ["price_value:pos"]),

    # Price & Value - Negative
    ("Grossly overpriced for what you get, missing basic features found in cheaper vehicles.", ["price_value:neg"]),
    ("Depreciation is catastrophic, lost 40% of its sticker price in just 18 months.", ["price_value:neg"]),
    ("Hidden subscription fees for heated seats and navigation make it feel like highway robbery.", ["price_value:neg"]),
    ("Insurance premiums are outrageously expensive compared to equivalent gasoline cars.", ["price_value:neg"]),

    # Customer Service - Positive
    ("Service center appointment was prompt, friendly staff, and got a free loaner vehicle.", ["customer_service:pos"]),
    ("Mobile service tech arrived at my driveway and replaced the 12V battery within 20 minutes.", ["customer_service:pos"]),
    ("Warranty claim on the AC compressor was approved instantly without any hassle.", ["customer_service:pos"]),
    ("Attentive customer support team who kept me updated through every step of delivery.", ["customer_service:pos"]),

    # Customer Service - Negative
    ("Horrendous customer service, waited three weeks just to get a diagnostic appointment.", ["customer_service:neg"]),
    ("The dealership refused to honor the warranty and blamed me for the motor failure.", ["customer_service:neg"]),
    ("Car sat at the service center for two months waiting on a simple replacement part.", ["customer_service:neg"]),
    ("Impossible to reach a human on the phone, service tickets get closed without resolution.", ["customer_service:neg"]),

    # Reliability - Positive
    ("100,000 trouble-free miles with zero mechanical failures, absolute peak reliability.", ["reliability:pos"]),
    ("Turn-key reliability every single morning, never stranded or triggered a warning light.", ["reliability:pos"]),
    ("Durable powertrain and dependable electronics that withstand extreme temperatures.", ["reliability:pos"]),
    ("Has proven far more reliable than any German luxury vehicle I've owned previously.", ["reliability:pos"]),

    # Reliability - Negative
    ("Left me completely stranded on the highway with 'Electrical System Fault' at 5,000 miles.", ["reliability:neg"]),
    ("Constant breakdowns and error codes, car has been in the shop four times in six months.", ["reliability:neg"]),
    ("The 12V battery died unexpectedly and bricked the entire car in my garage.", ["reliability:neg"]),
    ("Major drive unit failure required a full powertrain replacement under 15k miles.", ["reliability:neg"]),

    # Space & Practicality - Positive
    ("Enormous cargo room with the deep trunk and huge front trunk (frunk) for dirty gear.", ["space_practicality:pos"]),
    ("Plenty of legroom and headroom in the rear seats for tall adults, great family road-tripper.", ["space_practicality:pos"]),
    ("Clever center console storage and completely flat rear floor make it super versatile.", ["space_practicality:pos"]),
    ("Fold-flat rear seats easily accommodate two full-size bicycles without removing wheels.", ["space_practicality:pos"]),

    # Space & Practicality - Negative
    ("Rear passenger legroom is cramped and the sloping roofline severely cuts into headroom.", ["space_practicality:neg"]),
    ("Tiny trunk opening with no underfloor storage and completely lacks a front trunk.", ["space_practicality:neg"]),
    ("Very few cup holders or cubbies for phones, cabin storage design is poorly thought out.", ["space_practicality:neg"]),
    ("Impractical rear visibility due to tiny rear glass, difficult to carry bulky luggage.", ["space_practicality:neg"]),
]

ASPECT_DISPLAY_NAMES = {
    "range_battery": "Battery & Range",
    "charging": "Charging & Infrastructure",
    "performance": "Performance & Handling",
    "software_infotainment": "Software & Infotainment",
    "interior_comfort": "Interior & Comfort",
    "build_quality": "Build Quality & Exterior",
    "safety_driver_assist": "Safety & Driver Assistance",
    "price_value": "Price & Value",
    "customer_service": "Customer Service & Warranty",
    "reliability": "Reliability & Durability",
    "space_practicality": "Space & Practicality",
}

ALL_LABELS = [
    f"{aspect}:{polarity}"
    for aspect in ASPECT_DISPLAY_NAMES.keys()
    for polarity in ("pos", "neg")
]
