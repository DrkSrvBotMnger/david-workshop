# 🧭 Implementation Roadmap (by system)


## 🥉 3. Shop System
### Feature	Command	Status
- Show in-shop rewards (by active event)	/shop	⏳
- Filter/paginate by event priority	internal	⏳
- Buy reward (points + inventory update)	/buy <reward>	⏳
- Prevent repurchase if not stackable	internal	⏳

### 📌 Rules:

- availability == "inshop"
- If reward_type == preset: must be published
- Prioritize rewards by event priority

## 🟩 4. User Actions
Feature	Command	Status
Report self-reportable action	/report_action <action>	⏳
Grant points or reward based on action-event	internal	⏳

📌 Already functional via schema — just needs UI hookup
## 🟦 5. Mod Tools
Feature	Command	Status
Grant points	/admin grantpoints <user> <amount>	⏳
Take points	/admin takepoints <user> <amount>	⏳
Grant reward manually	/admin grantreward <user> <reward>	⏳
Take reward manually	/admin takereward <user> <reward>	⏳
View user log (points/rewards)	/admin userlog <user>	⏳