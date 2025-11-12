import config
from config import ADMIN_BOT_USERNAME

IMG = [
    "https://graph.org/file/d81baf8451cf1627ae3f6-c819d31887f32db07d.jpg",
    "https://graph.org/file/b29c2581eab59309d72cf-86cea750f2e54d6798.jpg",
    "https://graph.org/file/37eae141246f30803c113-f2a0774fc851ca0562.jpg",
    "https://graph.org/file/4afaa8ad4b2f757bdf9d7-47d5f883ea944a498d.jpg",
    "https://graph.org/file/153308ce2d6f968e25965-d310556f3d191bcc62.jpg",
]


START_TXT = """
**Hello, {}!**

<blockquote>
Welcome to <b>LUCIFER EXTRACTOR</b> — a powerful tool designed for efficient and organized course extraction.  
Using advanced automation, it simplifies the process of accessing structured course content with accuracy.
</blockquote>

<blockquote>
🌿 <b>Maintained by:</b> <a href="https://t.me/urs_lucifer">Admin</a>
</blockquote>
"""


FORCE_MSG = """
**Hello, {}**

<blockquote>
It seems you haven’t joined our official updates channel yet.  
Please join to continue using the extractor and stay informed about future updates.
</blockquote>

<blockquote>
🌿 <b>Maintained by:</b> <a href="https://t.me/urs_lucifer">Admin</a>
</blockquote>
"""


MODES_TXT = """
<blockquote>
Welcome to the <b>Modes Section</b>.  
Here, you can select between two operation types:
</blockquote>

• <b>Login Mode</b> – for authenticated extraction.  
• <b>Without Login</b> – for direct access without credentials.
"""


CUSTOM_TXT = """
⌬ **﹝Without Login﹞**

<blockquote>
In this mode, you can extract data using a course link directly.  
However, some features may require premium access for full functionality.
</blockquote>
"""


MANUAL_TXT = """
⌬ **﹝Login﹞**

<blockquote>
This mode allows personalized extraction using authentication.  
Simply choose the appropriate option provided and follow the guided process.
</blockquote>
"""


PLANS_TXT = """
⌬ **﹝Premium﹞**

<blockquote>
Welcome to the premium section.  
Subscribers enjoy enhanced features, faster extraction speeds, and priority support.
</blockquote>

<blockquote>
⚠️ After sending your payment screenshot, please allow some time for verification and activation.
</blockquote>

<blockquote>
🌿 <b>Maintained by:</b> <a href="https://t.me/urs_lucifer">Admin</a>
</blockquote>
"""


FREE_TXT = """
⌬ **﹝Free Trial﹞**
<b>
🏆 <u>Trial Access</u> — Valid for 5 minutes  
• Access limited course features  
• Preview extractor performance  
</b>
"""


BRONZE_TXT = """
⌬ **﹝Bronze Plan﹞**
<b>
🥉 <u>Bronze Membership</u>  
⏰ Validity: 7 Days  
💸 Price: ₹300
</b>
"""


SILVER_TXT = """
⌬ **﹝Silver Plan﹞**
<b>
🥈 <u>Silver Membership</u>  
⏰ Validity: 15 Days  
💸 Price: ₹500
</b>
"""


GOLD_TXT = """
⌬ **﹝Gold Plan﹞**
<b>
🥇 <u>Gold Membership</u>  
⏰ Validity: 30 Days  
💸 Price: ₹800
</b>
"""


OTHER_TXT = """
⌬ **﹝Custom Plans﹞**
<b>
🎁 <u>Customized Access</u>  
⏰ Duration: Flexible  
💸 Pricing: Based on selected period  

👨‍💻 Contact the administrator to configure your personalized plan.
</b>
"""


PAYMENT_TXT = """
<b>
⚜️ <u>Payment Instructions</u>

Please complete the payment based on your selected plan to activate premium features.  

📸 Scan QR Code → <a href='https://graph.org/file/2fbd9fda0f646b1422f05-218a2421d48d601d10.jpg'>View Payment QR</a>  

After payment, send a screenshot for confirmation.  
Processing may take a few minutes.
</b>
"""
