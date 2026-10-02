"""
send_business_quote_sms.py

Sends one quote per day about business, leadership, management, or
classic strategy (Art of War, 48 Laws of Power) as a real SMS.

HOW IT PICKS A QUOTE:
  1. If API_NINJAS_KEY is set, it first tries to fetch a fresh quote from
     the API Ninjas Quotes API (api-ninjas.com) in a random category:
     business, leadership, success, or money.
  2. If that fails for any reason (no key, network error, rate limit,
     bad response), it falls back to a curated local pool covering
     business, leadership, management, Art of War, and 48 Laws of Power
     themes. These are paraphrased in plain language rather than quoted
     verbatim from the books.
  3. The local pool has no-repeat memory (shared sent_state.json), same
     as the other scripts. The live API doesn't need this since it
     returns something different essentially every call.

SETUP:
  1. (Optional but recommended) Sign up free at https://api-ninjas.com,
     get an API key, and set it as the API_NINJAS_KEY secret. Without it,
     this script just uses the local pool every day, which still works
     fine, just isn't "fresh from the web."
  2. Same SMSGATEWAY_LOGIN / SMSGATEWAY_PASSWORD secrets as the other
     scripts, plus its own DAILY_QUOTE_RECIPIENT_NUMBER secret (separate
     from RECIPIENT_PHONE_NUMBER, so this can go to a different number
     if you want).

Optional env vars for testing:
  FORCE_FALLBACK=1   skip the API call and use the local pool directly
  DRY_RUN=1          print instead of sending
"""

import json
import os
import random

import requests
from requests.auth import HTTPBasicAuth

SMSGATEWAY_LOGIN = os.environ.get("SMSGATEWAY_LOGIN")
SMSGATEWAY_PASSWORD = os.environ.get("SMSGATEWAY_PASSWORD")
DAILY_QUOTE_RECIPIENT_NUMBER = os.environ.get("DAILY_QUOTE_RECIPIENT_NUMBER")
API_NINJAS_KEY = os.environ.get("API_NINJAS_KEY", "").strip()

SMSGATEWAY_URL = "https://api.sms-gate.app/3rdparty/v1/messages"
API_NINJAS_URL = "https://api.api-ninjas.com/v1/quotes"
API_CATEGORIES = ["business", "leadership", "success", "money"]

DRY_RUN = os.environ.get("DRY_RUN", "").strip() == "1"
FORCE_FALLBACK = os.environ.get("FORCE_FALLBACK", "").strip() == "1"

STATE_FILE = os.environ.get("STATE_FILE", "sent_state.json")

# ---- Curated fallback pool: business, leadership, management, Art of
# War, and 48 Laws of Power themes, paraphrased in plain language. ----
FALLBACK_QUOTES = [
    "Know the terrain before you commit to the fight - Sun Tzu's point was that information beats effort every time.",
    "The Art of War's core idea: the best wins are the ones where the other side never saw a real fight coming.",
    "Greene's 48 Laws often repeat one theme - guard your reputation, because it's the only thing people act on before they know you.",
    "Good management isn't control, it's removing the obstacles between your team and good work.",
    "Sun Tzu argued every battle is won before it's fought, in the planning, not the execution.",
    "One of the 48 Laws: never outshine the master - read the room before you show everyone what you're capable of.",
    "Leadership is deciding what NOT to do as much as what to do - focus is a strategy, not a side effect.",
    "Drucker's old line still holds: management is doing things right, leadership is doing the right things.",
    "The Art of War's advice on timing: know when to attack, and know when waiting IS the strategy.",
    "48 Laws of Power logic: keep others dependent on you, not the other way around - leverage comes from being needed.",
    "Real leadership shows up most clearly in how a team handles a bad week, not a good one.",
    "Sun Tzu: all warfare is based on deception - in business, that often just means not showing your full hand too early.",
    "One Greene principle worth remembering: win through actions, never through argument - results speak louder.",
    "Good businesses solve a problem; great ones make the problem disappear before customers notice it existed.",
    "The Art of War again: supreme excellence is breaking resistance without a fight - the cleanest wins avoid conflict altogether.",
    "48 Laws: always say less than necessary - the less you reveal, the more power you keep in a negotiation.",
    "Management tip as old as business itself: hire for trust, train for skill - skill is teachable, trust mostly isn't.",
    "Sun Tzu's view on competition: if you know yourself and your rival, the outcome is rarely a surprise.",
    "A Greene favorite: court attention at all costs - visibility, used wisely, compounds like interest.",
    "Leadership lesson: people don't remember your title, they remember how you made decisions under pressure.",
    "The Art of War reminds us speed matters - a mediocre plan executed fast often beats a perfect plan executed late.",
    "48 Laws: keep your allies close, but never fully owe anyone a favor you can't repay.",
    "Strategy, at its core, is just resource allocation - where you spend time and money says more than any mission statement.",
    "Sun Tzu's quiet point: the general who wins makes many calculations before battle, the one who loses makes few.",
    "48 Laws - Conceal your intentions: a company quietly bought up a rival's key suppliers before anyone knew an acquisition was coming, so no one could outbid them.",
    "48 Laws - Win through actions, not argument: instead of debating a skeptical client, a founder just shipped a working prototype and let the result make the case.",
    "48 Laws - Crush your enemy totally: a business that only half-solved a competitor's weakness watched that competitor come back stronger within a year.",
    "48 Laws - Use absence to raise your value: a sought-after consultant deliberately limited his availability, and both demand and his rates kept climbing.",
    "48 Laws - Enter with boldness: a job candidate who directly asked for the role they wanted, instead of hedging, got taken far more seriously than the cautious applicants.",
    "48 Laws - Know what truly motivates each person: a manager who learned one team member wanted recognition and another wanted autonomy got buy-in without forcing anything.",
    "48 Laws - Think freely, behave conventionally: a reformer who kept bold ideas private while following normal office norms avoided getting pushed out before real change was possible.",
    "48 Laws - Stay adaptable, assume no fixed shape: a company that kept reinventing its business model survived three industry shifts that wiped out more rigid competitors.",
    "Sun Tzu: appear weaker than you are when you're strong, and stronger than you are when you're weak - perception shapes what rivals choose to risk.",
    "The Art of War's core bet: the ultimate skill is winning without ever having to fight - conflict itself is often a sign the planning failed earlier.",
    "Sun Tzu again: opportunities multiply as they're seized - waiting for the perfect moment often means missing every workable one.",
    "Made to Stick's point: ideas spread when they're simple and concrete - a nutrition label works better than a lecture on calories.",
    "From Made to Stick: a surprising fact gets remembered longer than one that just confirms what people already believed.",
    "Made to Stick's lesson: one specific customer story often persuades more than a spreadsheet full of satisfaction scores.",
    "Blue Ocean Strategy's idea: stop competing on the same features as everyone else, and build a market space rivals aren't even looking at.",
    "Blue Ocean's favorite example: Cirque du Soleil dropped animal acts and ticket-price wars entirely, and built an entirely new audience instead of fighting over the old one.",
    "Blue Ocean Strategy: value innovation means cutting costs and raising value at the same time, not treating them as a trade-off.",
    "The Toyota Way: stop the line the moment a defect appears, instead of letting small problems pile up downstream into big ones.",
    "Toyota's principle: small, constant improvements beat one big redesign that nobody keeps maintaining afterward.",
    "The Toyota Way treats respect for people and continuous improvement as the same discipline, just aimed at different problems.",
    "Ferriss's line from The 4-Hour Work Week: being busy is often just a form of laziness - lazy thinking and indiscriminate action.",
    "The 4-Hour Work Week's point: outsourcing the predictable parts of your work frees up time for the parts only you can actually do.",
    "Ferriss again: define what 'enough' looks like before chasing more - most people grow without ever picking a finish line.",
    "Zero to One's core idea: going from 0 to 1 means building something genuinely new, not copying what already works - that's where real value gets created.",
    "Thiel's question from Zero to One: a startup's biggest risk isn't poor execution, it's never asking what's true that nobody else agrees with yet.",
    "Zero to One: competition erodes profit - a small monopoly in an overlooked niche usually beats a crowded, competitive market.",
    "Atomic Habits' line: you don't rise to the level of your goals, you fall to the level of your systems - the habit matters more than the ambition.",
    "Atomic Habits: make good habits obvious and bad habits invisible - environment design beats willpower on most days.",
    "Atomic Habits' math: getting just 1% better each day compounds into a completely different trajectory a year later.",
    "The Obstacle Is the Way's core line: the obstacle in the path becomes the path - what blocks you can become the way through, once you change how you see it.",
    "Holiday's Stoic point: you don't control events, only your response to them - that's the only lever that actually works.",
    "Good to Great's warning: good is the enemy of great - most companies never become great because they settle for merely good.",
    "Good to Great's advice: get the right people on the bus before deciding where the bus is even going.",
    "Collins's hedgehog concept: find the one thing you can be best in the world at, and ignore everything adjacent to it.",
    "Ready, Fire, Aim's lesson: most failed businesses didn't fail from a bad idea, they failed from overplanning before ever actually selling anything.",
    "Masterson's point in Ready, Fire, Aim: sell first and perfect later - the market tells you what to build better than any business plan does.",
    "Traction's rule: a business without a clear, ranked set of priorities drifts, even when everyone's individually working hard.",
    "Traction's point: fewer priorities, clearly ranked, beat a long list that everyone quietly ignores.",
    "Tony Robbins's line: the quality of your life is the quality of your decisions, made in a split second, usually under pressure.",
    "Awaken the Giant Within's idea: real change happens when the pain of staying the same finally outweighs the pain of changing.",
    "Extreme Ownership's central claim: there are no bad teams, only bad leaders - leaders own every outcome, good or bad, no exceptions.",
    "Willink and Babin's point: decentralized command only works when every person understands the mission well enough to make the call themselves.",
    "48 Laws - Cultivate an air of unpredictability: a negotiator who never confirmed his next move in advance kept the other side constantly adjusting to him instead of the reverse.",
    "48 Laws - Don't commit to one side too early: a mediator who avoided publicly siding with either department kept both sides' trust when a real conflict needed resolving later.",
    "48 Laws - Re-create yourself after a setback: an executive who openly rebranded his image after a failed venture rebuilt credibility faster than one who kept defending the old story.",
    "48 Laws - Play to people's fantasies, not just their needs: a product pitched on the outcome people wanted - freedom, status - sold better than one pitched purely on specs.",
    "48 Laws - Never appear too perfect: a leader who admitted one visible flaw came across as more trustworthy to their team than one who projected total confidence.",
    "Sun Tzu: he who knows when he can fight, and when he cannot, will be the one left standing.",
    "The Art of War's reminder: in the middle of chaos, there's usually an opportunity nobody else is calm enough to see yet.",
    "Sun Tzu's rhythm: move fast as the wind, stay still as the forest, strike like fire, hold firm like a mountain - match your pace to the moment, not a fixed style.",
    "Start With Why's core claim: people don't buy what you do, they buy why you do it.",
    "Sinek's point: a clear sense of purpose attracts loyalty long before any feature list could.",
    "The Lean Startup's method: build the smallest possible version of an idea, test it on real users, then adjust - before investing in anything bigger.",
    "Ries's point in The Lean Startup: a startup's real job isn't executing a fixed plan, it's finding a repeatable business model through constant testing.",
    "Horowitz's point: there's no formula for the hardest calls in business - just a willingness to decide anyway, with incomplete information.",
    "The Hard Thing About Hard Things: how you deliver bad news to your team often matters more than the bad news itself.",
    "Voss's negotiation rule in Never Split the Difference: 'no' isn't rejection, it's often just the real conversation finally starting.",
    "Never Split the Difference's trick: mirroring the last few words someone says gets them to keep explaining, almost without noticing they're doing it.",
    "Kahneman's distinction: fast, intuitive thinking is efficient but easily fooled; slow, deliberate thinking is accurate but effortful and often skipped.",
    "Thinking, Fast and Slow's warning: people are usually more confident in a snap judgment than the evidence actually justifies.",
    "Christensen's warning: successful companies often get disrupted not by ignoring their customers, but by listening too closely to the ones they already have.",
    "The Innovator's Dilemma: a cheaper, simpler product aimed at ignored customers can eventually outgrow the market leader's premium offering.",
    "Phil Knight's lesson from Shoe Dog: nearly every early version of Nike was one bad quarter away from folding - persistence simply outlasted every near-failure.",
    "Dalio's rule in Principles: pain plus reflection equals progress - a mistake only compounds into growth if you actually sit down and study it.",
    "Principles' idea: radical transparency inside a team surfaces real problems faster than politeness ever will.",
    "Newport's argument in Deep Work: the ability to focus without distraction is getting rarer, and rare skills are valuable skills.",
    "Deep Work's point: shallow, reactive tasks feel productive in the moment but rarely move anything important forward.",
    "The Dichotomy of Leadership's idea: a good leader stays aggressive without being reckless, confident without being arrogant - balance beats either extreme.",
    "48 Laws - Learn to use enemies, don't over-trust friends: a manager who gave a skeptical critic real responsibility turned them into the project's fiercest defender.",
    "48 Laws - Get others to do the work, take the credit where it counts: a lead engineer who let a junior present the team's fix to leadership built loyalty that paid off for years.",
    "48 Laws - Make people come to you: a founder who stopped chasing investors and instead built something press wrote about found funding calls coming in unsolicited.",
    "48 Laws - Avoid the chronically unlucky and unhappy: a hiring manager noticed every role filled by one particular referral ended in conflict, and stopped taking that referral's recommendations.",
    "48 Laws - Use selective generosity to disarm resistance: a vendor who absorbed one client's small billing mistake without complaint won a much bigger contract the next quarter.",
    "48 Laws - Appeal to self-interest, not sympathy, when asking for help: a request framed as 'this also solves your problem' got approved far faster than one framed as a favor.",
    "48 Laws - Act as a friend, observe as a spy: a new hire who stayed quiet in meetings for the first month learned more about real office politics than any onboarding doc could teach.",
    "48 Laws - Don't wall yourself off completely: a founder who refused all outside feedback missed the warning signs a more connected competitor caught months earlier.",
    "48 Laws - Know exactly who you're dealing with: a sales rep who treated a quiet technical buyer the same as a chatty executive lost the deal to someone who read the room first.",
    "48 Laws - Seem less sharp than you are: a candidate who let an interviewer 'discover' the right answer instead of stating it outright was remembered as a great collaborator.",
    "48 Laws - Turn apparent weakness into leverage: a startup that openly admitted a product gap to customers earned more trust than a competitor who pretended to have no flaws.",
    "48 Laws - Concentrate your resources instead of spreading thin: a small team that focused on one feature beat a rival splitting effort across five mediocre ones.",
    "48 Laws - Play the role the room expects, even while scheming your next move: a junior exec who stayed visibly loyal to a sinking project quietly built support for the pivot that replaced it.",
    "48 Laws - Keep your own hands clean: an executive who let a trusted deputy deliver all the unpopular decisions kept his own reputation intact through a rocky reorg.",
    "48 Laws - Build belief, not just agreement: a brand that sold an identity and a cause, not just a product, kept customers who never once compared specs to competitors.",
    "48 Laws - Plan the whole sequence, not just the opening move: a negotiator who had already mapped out moves four steps ahead closed the deal before the other side even sensed the direction.",
    "48 Laws - Make hard work look effortless: a presenter who rehearsed for weeks delivered a pitch that looked improvised, and the room assumed it was pure natural talent.",
    "48 Laws - Control the options you offer others: a manager who gave two acceptable choices instead of an open question got the outcome they wanted without ever issuing an order.",
    "48 Laws - Act with quiet authority, not just a title: an interim lead who carried themselves like the permanent choice was treated like one well before the official decision came.",
    "48 Laws - Master timing over raw effort: a product launched three months later, once the market was actually ready, outsold an earlier rival that shipped first but too soon.",
    "48 Laws - Let go of what you can't have, visibly: a founder who stopped chasing a investor who'd already passed twice found other backers took the company more seriously.",
    "48 Laws - Create a moment worth remembering: a company that turned a routine product update into a live event got more coverage than months of ordinary press releases.",
    "48 Laws - Stir things up to reveal where people really stand: a leader who floated a controversial idea in a meeting learned who'd actually support change before committing to it.",
    "48 Laws - Be wary of the free lunch: a partnership offered with no clear ask attached turned out to come with strings nobody noticed until it was too late to back out easily.",
    "48 Laws - Think twice before replacing a legend: a successor who tried to run things exactly like their predecessor struggled, while one who openly charted a new path earned the room's patience.",
    "48 Laws - Remove the source, not just the symptom: a team that replaced one disruptive influence saw unrelated problems across the group quietly disappear too.",
    "48 Laws - Win hearts before you win arguments: a manager who spent a month building trust got a reluctant team to adopt a hard change far faster than one who just issued the directive.",
    "48 Laws - Reflect people's own thinking back at them: a negotiator who repeated the other side's own words back to them got agreement faster than one who kept making new arguments.",
    "48 Laws - Introduce change gradually, not all at once: a leader who rolled out a new process team by team avoided the backlash a company-wide overnight switch triggered elsewhere.",
    "48 Laws - Know when you've already won: a company that kept pushing after beating a rival on price ended up in a margin war neither side actually needed to have.",
    "Sun Tzu: know the enemy and know yourself, and in a hundred contests you'll never be in real danger.",
    "The Art of War: all men can see the tactics by which a victory is won, but none can see the strategy that led up to it.",
    "Sun Tzu's point on deception: when able to attack, appear unable; when using forces, appear inactive - let your rival misjudge you.",
    "The Art of War: the clever fighter chooses the moment, never letting the opponent dictate the terms of the engagement.",
    "Sun Tzu: subduing the enemy without fighting is the height of skill - the best campaigns look almost uneventful from the outside.",
    "The Art of War on preparation: victorious strategists win first and then go to battle, while the defeated battle first and hope to win.",
    "Sun Tzu's advice on information: those who know both their own strengths and their rival's will never be caught off guard.",
    "The Art of War: a leader who treats their people with genuine care earns loyalty no order could ever force into existence.",
    "Sun Tzu on flexibility: water takes the shape of whatever contains it - a strategy that can't adapt to new terrain eventually breaks.",
    "The Art of War: the supreme commander wins the campaign before the first move is even made, through preparation nobody else sees.",
    "Built to Last's finding: enduring companies are built around a core purpose that barely changes, even as products and markets shift constantly around it.",
    "Collins and Porras argue great companies set audacious long-term goals, then organize everything underneath them to make the goal unavoidable.",
    "The E-Myth Revisited's warning: being great at the craft doesn't make you great at running the business built around that craft - they're different skills entirely.",
    "Gerber's point: build systems so the business works without you, instead of building a job that only works because of you.",
    "Crossing the Chasm's idea: the hardest part of a new product's life isn't the early adopters, it's convincing the skeptical mainstream after them.",
    "Moore's advice: win one specific niche completely before trying to serve everyone - credibility in a narrow market spreads outward.",
    "The Innovator's Solution's point: disruption usually starts by being worse on the metrics incumbents care about, and better on the ones new customers actually need.",
    "Christensen's follow-up advice: build a separate team with its own incentives to pursue a disruptive idea, since the main business will always starve it of resources otherwise.",
    "Duckworth's research in Grit: sustained passion plus sustained persistence predicts long-term success better than raw talent alone.",
    "Grit's finding: people who stick with hard things long enough to get good at them usually end up looking more talented than people who quit early and try something new.",
    "Dweck's distinction in Mindset: believing ability can be developed, not just inherited, changes how people respond to failure entirely.",
    "Mindset's point: praising effort and strategy builds resilience, while praising innate talent quietly makes people afraid to be challenged.",
    "The Power of Habit's model: every habit runs on a cue, a routine, and a reward - change the routine and keep the same cue and reward, and the habit shifts.",
    "Duhigg's idea: a single 'keystone habit' can trigger a cascade of other improvements without directly targeting them at all.",
    "Cialdini's research in Influence: people say yes more easily when they feel they already owe something, even something small and unasked for.",
    "Influence's point: scarcity doesn't just create urgency, it makes people value something more simply because it might not be available.",
    "Getting to Yes's core move: separate the people from the problem, so personal friction doesn't block an otherwise workable deal.",
    "The book's advice: negotiate around underlying interests, not stated positions - two sides often want the same outcome through different demands.",
    "Covey's distinction: effective people focus on what they can influence, not just what concerns them - energy spent on the uncontrollable is energy wasted.",
    "The 7 Habits' idea: sharpening the saw - deliberately investing in your own renewal - prevents the slow decline that busy, undermaintained people eventually hit.",
    "Carnegie's old rule still holds: people care far more about their own name, their own problems, and their own wins than about yours.",
    "How to Win Friends' point: genuine interest in someone else opens more doors in two months than trying to interest them in you ever will.",
    "The One Minute Manager's idea: specific, immediate feedback - good or bad - changes behavior faster than a vague review months after the fact.",
    "Who Moved My Cheese's lesson: the people who adapt fastest to a changed situation are usually the ones who stopped assuming things would stay the same.",
    "Lencioni's model: teams fail in layers - no trust leads to no real conflict, which leads to no commitment, no accountability, and finally no results.",
    "The Five Dysfunctions' point: a team that avoids healthy disagreement usually isn't being polite, it's quietly setting itself up to fail later.",
    "Multipliers' distinction: some leaders amplify the intelligence of everyone around them, while others - often without meaning to - shrink it.",
    "Wiseman's research: asking better questions got more out of a team than any leader's own expertise ever could.",
    "Radical Candor's formula: care personally and challenge directly - skip either half, and feedback turns into either empty praise or pure cruelty.",
    "Seth Godin's Purple Cow idea: in a crowded market, 'very good' is invisible - only genuinely remarkable work gets talked about at all.",
    "This Is Marketing's point: marketing isn't interrupting strangers, it's building something a specific group of people already wanted to find.",
    "Contagious's research: ideas spread when they carry social currency - sharing them makes the sharer look good, informed, or in the know.",
    "The Tipping Point's idea: small, specific changes in a product or message can trigger an outsized shift once it reaches the right few connectors.",
    "Gladwell's Outliers argument: extreme success usually traces back to accumulated advantage and timing, not just raw individual merit.",
    "David and Goliath's reframe: what looks like a disadvantage - size, resources, experience - sometimes forces a strategy the 'stronger' side can't match.",
    "Think and Grow Rich's old claim: a specific, burning goal written down and revisited daily shapes decisions in ways a vague wish never does.",
    "Rich Dad Poor Dad's core distinction: assets put money in your pocket, liabilities take it out - most people quietly confuse the two their whole lives.",
    "Housel's point in The Psychology of Money: staying wealthy requires different skills than getting wealthy - mainly fear, humility, and not pushing your luck.",
    "Scaling Up's warning: the habits that got a company to its first ten people often actively break once it tries to grow past a hundred.",
    "Goldratt's Theory of Constraints from The Goal: a system's output is limited by its single slowest step - fixing anything else barely moves the result.",
    "Measure What Matters' idea: ambitious goals paired with measurable key results keep teams aligned without needing constant top-down direction.",
    "Andy Grove's High Output Management: a manager's output is the output of their team plus the teams they influence, not their own personal task list.",
    "Grove's other idea: a 'strategic inflection point' - a shift so big it changes the rules of the industry - is survivable only if you spot it before it's obvious to everyone.",
    "Crucial Conversations' point: the conversations people avoid the most are usually the exact ones that would fix the problem fastest.",
    "Brene Brown's Dare to Lead: vulnerability from a leader - admitting uncertainty out loud - builds more trust than projecting constant certainty.",
    "Pink's Drive: once pay is fair, autonomy, mastery, and purpose motivate people far more reliably than bigger bonuses ever do.",
    "To Sell is Human's reframe: almost everyone is 'selling' something daily - an idea, a plan, themselves - whether or not they'd call it sales.",
    "The 4 Disciplines of Execution's rule: a team can realistically chase one or two wildly important goals at once - not six, no matter how important each feels.",
    "Geoff Smart's Who: most hiring mistakes come from skipping structured reference checks, not from a lack of good interview questions.",
    "The Ideal Team Player's model: look for people who are humble, hungry, and smart with people - missing any one of the three usually causes friction later.",
    "Basecamp's Rework: a smaller, simpler version shipped now beats a bigger, perfect version that never ships at all.",
    "Bad Blood's cautionary lesson: a culture where no one feels safe raising bad news is usually the first real sign a company is already in trouble.",
    "Isaacson's The Innovators: almost no major breakthrough came from a lone genius - it came from a small team combining different kinds of expertise.",
    "The Heath brothers' Switch: lasting change needs to appeal to both the rational planner and the emotional, resistant side of people - convincing only one half rarely sticks.",
    "Decisive's advice: widen your options before deciding - most bad calls come from only ever comparing two choices when more existed.",
    "The Checklist Manifesto's point: experts fail less from lack of knowledge and more from skipping simple steps under pressure - a short checklist catches what memory alone misses.",
    "Taleb's Antifragile: some systems don't just resist shocks, they actually get stronger from them - built with slack and optionality instead of false stability.",
    "The Black Swan's warning: the rare, unpredictable event you didn't plan for usually matters more than every trend you carefully forecasted.",
    "Freakonomics' approach: incentives explain more real-world behavior than good intentions do - look at what people are actually rewarded for, not what they claim to value.",
    "Hiring: a bad hire costs far more in team morale than in salary alone.",
    "Hiring: hiring for attitude and training for skill beats hiring for skill and hoping for attitude.",
    "Hiring: a slow hiring process loses the best candidates to faster competitors.",
    "Hiring: checking how someone treats support staff reveals more than how they act in the interview room.",
    "Hiring: one great hire often does the work of three average ones, quietly.",
    "Delegation: a leader who can't delegate has built a bottleneck, not a team.",
    "Delegation: delegating the outcome, not the exact method, lets people surprise you with a better approach.",
    "Delegation: holding onto every decision personally is often fear wearing the costume of diligence.",
    "Delegation: the real test of delegation is whether things still run well when you're unreachable.",
    "Feedback: feedback delayed by weeks has already lost most of its power to change behavior.",
    "Feedback: specific feedback changes actions, vague feedback just changes moods.",
    "Feedback: the hardest feedback to give is usually the most useful one to receive.",
    "Feedback: praising in public and correcting in private builds trust that lasts.",
    "Decision making: a decision made with 70 percent of the information, made on time, usually beats a perfect decision made too late.",
    "Decision making: most big decisions are reversible more often than fear suggests - treat the reversible ones lightly.",
    "Decision making: writing down the decision and the reasoning behind it makes it much easier to learn from later.",
    "Decision making: indecision is itself a decision, just one made by default instead of on purpose.",
    "Negotiation: the first number mentioned in a negotiation quietly anchors everything that follows.",
    "Negotiation: walking away calmly is often the strongest move at the table, not the weakest.",
    "Negotiation: understanding what the other side actually needs matters more than what they say they want.",
    "Negotiation: a deal both sides feel slightly unhappy with is often the sign of a fair one.",
    "Sales: people buy outcomes, not features - sell the after, not the specs.",
    "Sales: the best salespeople ask more questions than they answer.",
    "Sales: a customer who almost said no and stayed anyway becomes the most loyal one later.",
    "Sales: price objections are usually value objections wearing a different name.",
    "Marketing: a clear message to the right few beats a vague message to everyone.",
    "Marketing: consistency in a brand's voice builds more trust than any single clever campaign.",
    "Marketing: word of mouth still outperforms paid advertising when the product genuinely earns it.",
    "Marketing: knowing exactly who you're not for makes it much easier to speak clearly to who you are for.",
    "Finance: revenue is vanity, profit is sanity, cash flow is reality.",
    "Finance: a business can be profitable on paper and still die from running out of cash.",
    "Finance: small recurring costs add up faster than the big one-time ones people worry about.",
    "Finance: knowing your numbers cold changes how a room negotiates with you.",
    "Leadership: a leader's mood sets the ceiling for the whole team's mood that day.",
    "Leadership: people forget what a leader said in a crisis, but never how calm or panicked they seemed.",
    "Leadership: trust is built in small moments and lost in single large ones.",
    "Leadership: a title grants authority, but only consistent behavior earns real respect.",
    "Strategy: a strategy that fits on one page gets executed - one that fits in a binder usually doesn't.",
    "Strategy: saying no to good opportunities is what makes room for the great ones.",
    "Strategy: a clear strategy makes most day-to-day decisions obvious instead of debatable.",
    "Strategy: copying a competitor's strategy rarely works, since you're copying their move, not their position.",
    "Execution: ideas are cheap, consistent execution is the actual competitive advantage.",
    "Execution: a mediocre plan executed with full commitment usually beats a brilliant plan executed half-heartedly.",
    "Execution: momentum from small finished tasks builds more confidence than one big unfinished plan.",
    "Execution: most projects don't fail from a bad idea, they fail from unclear ownership of the next step.",
    "Innovation: most innovation is recombination - putting two existing ideas together in a way nobody tried yet.",
    "Innovation: the constraint that feels limiting is often exactly what forces the creative solution.",
    "Innovation: a culture afraid of small failures rarely produces any large successes either.",
    "Innovation: customers can describe their problems clearly far more often than they can describe the solution.",
    "Risk: the biggest risk is often the one nobody in the room is willing to name out loud.",
    "Risk: diversifying too early can be just as costly as not diversifying at all.",
    "Risk: a risk clearly written down and planned for is already half-managed.",
    "Risk: avoiding all risk is itself a risky strategy in a market that keeps moving.",
    "Culture: culture is what people do when no one with authority is watching.",
    "Culture: one tolerated bad behavior from a top performer teaches the whole team what's actually allowed.",
    "Culture: a strong culture doesn't need a thick handbook, it needs consistent leaders.",
    "Culture: what gets celebrated openly in a company is what quietly gets repeated by everyone else.",
    "Time management: busy and productive are not the same thing, and mistaking one for the other wastes years.",
    "Time management: protecting a few hours of uninterrupted focus often outproduces a whole day of meetings.",
    "Time management: saying yes to a new commitment is quietly saying no to something else already on the calendar.",
    "Time management: the urgent constantly crowds out the important unless something deliberately protects it.",
    "Customer focus: the loudest customer complaint is rarely the most common one worth fixing first.",
    "Customer focus: watching what customers actually do reveals more than asking what they say they want.",
    "Customer focus: a small group of unhappy customers often predicts a much larger wave quietly forming behind them.",
    "Customer focus: retaining an existing customer is usually cheaper than acquiring a new one to replace them.",
    "Pricing: pricing too low signals low value just as loudly as pricing too high signals arrogance.",
    "Pricing: a price increase loses fewer customers than most founders fear, if the value is clear.",
    "Pricing: bundling reframes a price comparison that would otherwise favor the cheaper competitor.",
    "Competition: watching a competitor too closely can quietly turn your strategy into a copy of theirs.",
    "Competition: a competitor's weakness is often more useful information than their strength.",
    "Competition: being first to market matters less than being first to actually satisfy the customer.",
    "Networking: a network built only when you need something feels exactly as transactional as it is.",
    "Networking: helping someone with no immediate ask attached is what people actually remember later.",
    "Networking: a wide shallow network matters less than a few relationships built on real trust.",
    "Branding: a brand is really just a promise, repeated consistently enough that people start to believe it.",
    "Branding: inconsistency between what a brand says and what it does erodes trust faster than silence would.",
    "Branding: the strongest brands make a clear choice about who they are not for.",
    "Scaling: what works at ten people often breaks quietly at a hundred, long before anyone notices why.",
    "Scaling: scaling a broken process just produces the same mistakes faster and at greater cost.",
    "Scaling: growth hides problems temporarily - a slowdown is usually when they all surface at once.",
    "Failure: a failure examined honestly is worth more than a success nobody bothered to study.",
    "Failure: the fastest learners treat failure as data, not as a verdict on their worth.",
    "Failure: most comebacks share one trait: the willingness to admit what actually went wrong first.",
    "Data-driven decisions: data tells you what happened, judgment still has to decide what to do about it.",
    "Data-driven decisions: a dashboard full of numbers nobody acts on is just decoration.",
    "Data-driven decisions: the metric a team is measured on quietly becomes the behavior that team optimizes for.",
    "Communication: clarity is a form of kindness - vague instructions cost everyone time later.",
    "Communication: what a leader repeats often is what a team assumes actually matters most.",
    "Communication: most conflict in a team traces back to an assumption nobody actually said out loud.",
    "Productivity: a to-do list with twenty items is really just a list of things that won't get done today.",
    "Productivity: finishing one meaningful task beats starting five that stay half-done.",
    "Productivity: energy management matters as much as time management - the hour matters less than the state you're in during it.",
    "Resilience: the obstacle that feels permanent rarely is - most setbacks are temporary if you keep moving.",
    "Resilience: resilience isn't the absence of difficulty, it's staying functional in the middle of it.",
    "Resilience: the comeback usually starts quietly, long before anyone outside notices anything changed.",
    "Focus: doing fewer things well beats doing many things adequately.",
    "Focus: a long list of priorities is really just a list, not a set of priorities at all.",
    "Focus: saying no to a decent opportunity is what keeps room open for a great one.",
    "Meetings: a meeting with no clear decision to make at the end could have been an email instead.",
    "Meetings: the most useful meetings end with one named owner for each next step, not just a summary.",
    "Meetings: inviting everyone who might care usually produces worse meetings than inviting only who must decide.",
    "Meetings: starting on time, even with half the room missing, teaches everyone to actually show up on time.",
    "Remote work: trust, not visible hours, is what actually makes a remote team work.",
    "Remote work: over-communicating in writing prevents the small misunderstandings that in-person teams fix by accident.",
    "Remote work: a remote team without deliberate informal connection slowly drifts into feeling like strangers.",
    "Customer service: how a company handles a complaint matters more to loyalty than whether the problem ever happened at all.",
    "Customer service: a fast, honest apology defuses more anger than a slow, perfect explanation.",
    "Customer service: customers rarely remember the mistake itself, they remember how quickly it got fixed.",
    "Operations: a process that only works when the best person runs it isn't actually a process yet.",
    "Operations: the bottleneck in a system is rarely where people assume it is until someone actually measures it.",
    "Operations: small inefficiencies repeated daily cost more over a year than one dramatic one-time mistake.",
    "Product management: a feature nobody asked for rarely gets used, no matter how impressive it was to build.",
    "Product management: shipping something small and learning from real use beats debating a big version in a conference room.",
    "Product management: the roadmap is a hypothesis, not a promise - the best teams stay willing to revise it.",
    "Startups: a startup doesn't die from running out of ideas, it dies from running out of cash before the idea works.",
    "Startups: the first version of almost everything is embarrassing, and shipping it anyway is the whole point.",
    "Startups: early traction with a tiny group of users who truly love the product beats broad indifference from a big one.",
    "Entrepreneurship: most successful founders didn't start with the final idea, they started by solving their own immediate problem.",
    "Entrepreneurship: the willingness to be wrong in public, early and often, separates founders who adapt from ones who don't.",
    "Entrepreneurship: an entrepreneur's real job is reducing uncertainty one small test at a time, not predicting the future perfectly.",
    "Investing: time in the market tends to beat timing the market, for most people, most of the time.",
    "Investing: the investor who panics and sells during a downturn usually locks in the loss that patience would have avoided.",
    "Investing: understanding what you're invested in matters more than chasing whatever performed best last year.",
    "Accountability: a deadline with no consequence attached quietly becomes a suggestion.",
    "Accountability: owning a mistake immediately, before anyone finds it, preserves more trust than a well-crafted excuse.",
    "Accountability: accountability works best when it's clear in advance, not improvised after something goes wrong.",
    "Trust: trust is built slowly through dozens of kept small promises, and lost quickly through one broken big one.",
    "Trust: a team that trusts its leader will forgive a bad call made in good faith far more easily than a good call explained poorly.",
    "Change management: people resist change less than they resist feeling like change is being done to them without warning.",
    "Change management: explaining the why behind a change gets more buy-in than any announcement of the what ever will.",
    "Change management: a change rolled out gradually, with room for feedback, sticks longer than one forced through overnight.",
    "Conflict resolution: most workplace conflict is really a disagreement about priorities, dressed up as a disagreement about people.",
    "Conflict resolution: addressing tension directly and early is almost always less costly than letting it quietly compound.",
    "Mentorship: a good mentor asks better questions far more often than they hand out direct answers.",
    "Mentorship: the fastest way to deepen your own understanding of something is to teach it to someone else.",
    "Work-life balance: burnout rarely announces itself suddenly, it builds quietly through months of ignored small warning signs.",
    "Work-life balance: protecting personal time isn't a lack of ambition, it's what makes sustained ambition possible at all.",
    "Creativity: constraints don't kill creativity, boundless unlimited choice usually does.",
    "Creativity: most creative breakthroughs come after a period of rest, not in the middle of forced, exhausted effort.",
    "Persuasion: people are persuaded far more by stories they can picture than by statistics they have to calculate.",
    "Persuasion: asking questions that lead someone to their own conclusion works better than arguing them into agreement.",
    "Onboarding: the first week at a new job quietly sets expectations that take months to undo if they're wrong.",
    "Onboarding: a new hire who feels useful in their first few days is far more likely to stay past their first year.",
    "Supply chain: a single point of failure in a supply chain is a risk hiding as an efficiency, until the day it isn't.",
    "Supply chain: redundancy costs money upfront and saves far more the one time it's actually needed.",
    "Goal setting: a goal without a deadline is really just a wish written down somewhere.",
    "Goal setting: specific numeric targets get hit far more often than vague intentions to 'improve'.",
    "Goal setting: breaking a big goal into weekly checkpoints makes a year-long target feel achievable instead of abstract.",
    "Goal setting: writing a goal down and reviewing it weekly keeps it from quietly sliding off the priority list.",
    "Team building: a team that's never disagreed openly probably hasn't been tested yet, not that it's especially harmonious.",
    "Team building: shared small wins build a team's confidence faster than any single motivational speech.",
    "Team building: diversity of thinking on a team catches blind spots that a room of similar people would miss entirely.",
    "Team building: psychological safety - feeling safe to speak up - predicts team performance better than raw talent does.",
    "Crisis management: how a leader communicates in the first 24 hours of a crisis shapes trust for months afterward.",
    "Crisis management: silence during a crisis gets filled with speculation, usually worse than the actual truth.",
    "Crisis management: a crisis plan written calmly in advance works far better than one improvised under pressure.",
    "Succession planning: a company with no successor identified for key roles is one resignation away from a real crisis.",
    "Succession planning: grooming a successor early, visibly, tends to make that person more loyal, not more likely to leave.",
    "Succession planning: the strongest leaders are measured partly by how well the organization runs after they're gone.",
    "Diversity and inclusion: a room full of agreement is often a room that's missing a perspective it badly needs.",
    "Diversity and inclusion: inclusion isn't just who gets hired, it's whose ideas actually get acted on afterward.",
    "Diversity and inclusion: homogeneous teams move fast early and hit blind spots later that diverse teams catch sooner.",
    "Employee engagement: people rarely quit a job, they quit a manager, or a lack of growth, or feeling unseen.",
    "Employee engagement: recognition that's specific and timely motivates more reliably than a generic year-end bonus.",
    "Employee engagement: an engaged employee solves problems before being asked, a disengaged one waits to be told.",
    "Business ethics: a shortcut that only works if nobody finds out isn't really a shortcut, it's a delayed cost.",
    "Business ethics: a company's true values show up in what it does under pressure, not what it prints in its handbook.",
    "Business ethics: long-term trust is worth more than almost any short-term gain that risks it.",
    "Learning: the fastest-growing people treat every mistake as tuition already paid, worth extracting a lesson from.",
]


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def pick_unused(key, pool, state):
    used = set(state.get(key, []))
    available = [m for m in pool if m not in used]
    if not available:
        print(f"All '{key}' quotes used. Resetting this pool.")
        available = pool[:]
        used = set()
    choice = random.choice(available)
    used.add(choice)
    state[key] = list(used)
    return choice


def fetch_api_quote():
    if not API_NINJAS_KEY or FORCE_FALLBACK:
        return None
    try:
        category = random.choice(API_CATEGORIES)
        response = requests.get(
            API_NINJAS_URL,
            headers={"X-Api-Key": API_NINJAS_KEY},
            params={"category": category},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            return None
        item = data[0]
        quote = item.get("quote", "").strip()
        author = item.get("author", "").strip()
        if not quote:
            return None
        return f'"{quote}" - {author}' if author else f'"{quote}"'
    except Exception as e:
        print(f"API quote fetch failed, falling back to local pool: {e}")
        return None


def send(numbers, text):
    if DRY_RUN:
        print(f"[dry run] would send to {numbers}: {text}")
        return
    response = requests.post(
        SMSGATEWAY_URL,
        json={"textMessage": {"text": text}, "phoneNumbers": numbers},
        auth=HTTPBasicAuth(SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD),
    )
    response.raise_for_status()
    print(f"Sent to {numbers}: {text}")


def send_message():
    if not DRY_RUN and not all([SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD, DAILY_QUOTE_RECIPIENT_NUMBER]):
        raise SystemExit(
            "Missing config. Set SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD, and "
            "DAILY_QUOTE_RECIPIENT_NUMBER as environment variables."
        )

    numbers = [n.strip() for n in (DAILY_QUOTE_RECIPIENT_NUMBER or "").split(",") if n.strip()]
    if not numbers:
        print("No recipients configured.")
        return

    state = load_state()

    text = fetch_api_quote()
    if text:
        print("Using a fresh quote from the API.")
    else:
        print("Using the local curated pool.")
        text = pick_unused("business_quote_fallback", FALLBACK_QUOTES, state)

    send(numbers, text)
    save_state(state)


if __name__ == "__main__":
    send_message()
