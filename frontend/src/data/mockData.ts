import { Customer, AgentInteraction } from '@/types/database'

export const INITIAL_CUSTOMERS: Customer[] = [
  {
    customer_id: 101,
    name: 'Sarah Jenkins',
    phone_number: '+1 (555) 234-8901',
    email: 'sarah.jenkins@example.com',
    language: 'English',
    lending_date: '2024-01-15',
    due_date: '2024-11-30',
    outstanding_amount: 1450.50,
    principal_amount: 5000.00,
    interest_rate: 11.50,
  },
  {
    customer_id: 102,
    name: 'Carlos Rodriguez',
    phone_number: '+1 (555) 876-5432',
    email: 'carlos.rodriguez@example.com',
    language: 'Spanish',
    lending_date: '2024-02-10',
    due_date: '2024-11-25',
    outstanding_amount: 3200.00,
    principal_amount: 7500.00,
    interest_rate: 13.25,
  },
  {
    customer_id: 103,
    name: 'Priya Sharma',
    phone_number: '+1 (555) 432-1098',
    email: 'priya.sharma@example.com',
    language: 'Hindi',
    lending_date: '2023-11-01',
    due_date: '2024-11-18',
    outstanding_amount: 850.00,
    principal_amount: 3000.00,
    interest_rate: 9.75,
  },
  {
    customer_id: 104,
    name: 'Marcus Vance',
    phone_number: '+1 (555) 901-2345',
    email: 'marcus.vance@example.com',
    language: 'English',
    lending_date: '2024-03-20',
    due_date: '2024-12-05',
    outstanding_amount: 6200.75,
    principal_amount: 10000.00,
    interest_rate: 14.00,
  },
  {
    customer_id: 105,
    name: 'Elena Rostova',
    phone_number: '+1 (555) 345-6789',
    email: 'elena.rostova@example.com',
    language: 'English',
    lending_date: '2024-04-05',
    due_date: '2024-11-15',
    outstanding_amount: 0.00,
    principal_amount: 4500.00,
    interest_rate: 10.50,
  },
  {
    customer_id: 106,
    name: 'David Chen',
    phone_number: '+1 (555) 654-3210',
    email: 'david.chen@example.com',
    language: 'English',
    lending_date: '2024-05-12',
    due_date: '2024-12-10',
    outstanding_amount: 2750.25,
    principal_amount: 6000.00,
    interest_rate: 12.00,
  },
]

export const INITIAL_INTERACTIONS: AgentInteraction[] = [
  {
    interaction_id: 1,
    customer_id: 101,
    call_datetime: '2024-11-20T10:30:00Z',
    call_status: 'Completed',
    language_used: 'English',
    call_transcript: `[Agent]: Hello, am I speaking with Sarah Jenkins?
[Customer]: Yes, this is Sarah. Who is calling?
[Agent]: This is Alex from Loan Care Services regarding your overdue balance of ₹1,450.50 due on November 30th. We're calling to see if we can help set up a payment arrangement today.
[Customer]: Oh hi Alex. I apologize, I had some unexpected medical expenses this month. I get my paycheck next Friday.
[Agent]: I understand, Sarah. Thank you for letting us know. Would you be able to commit to paying ₹750 by next Friday, November 29th, to keep the account in good standing?
[Customer]: Yes, absolutely! I can pay ₹750 on November 29th without fail.
[Agent]: Perfect. I have noted your Promise to Pay of ₹750 for November 29th. We'll send an SMS confirmation to this number. Thank you for your cooperation!
[Customer]: Thank you for working with me, Alex. Have a great day.`,
    call_summary: 'Customer acknowledged outstanding balance. Explained medical delay and committed to a partial Promise to Pay (PTP) of ₹750.00 on November 29th. SMS confirmation sent.',
    customer_feedback: 'Customer was cooperative, polite, and expressed relief at flexible payment arrangement options.',
    payment_status: 'Promised to Pay',
    promise_to_pay_date: '2024-11-29',
    promise_to_pay_amount: 750.00,
    call_recording: 'https://actions.google.com/sounds/v1/speech/female_voice_prompt.ogg',
  },
  {
    interaction_id: 2,
    customer_id: 102,
    call_datetime: '2024-11-19T14:15:00Z',
    call_status: 'Completed',
    language_used: 'Spanish',
    call_transcript: `[Agent]: Hola, buenas tardes. ¿Hablo con el señor Carlos Rodríguez?
[Customer]: Sí, con él habla. ¿De parte de quién?
[Agent]: Le llama Sofía del departamento de cobranza sobre su cuenta pendiente de ₹3,200.00.
[Customer]: Hola Sofía. Sí, estoy al tanto. Mi negocio estuvo un poco lento estas semanas, pero mañana recibiré el cobro de un cliente.
[Agent]: Comprendo, señor Rodríguez. ¿Podría realizar un abono parcial de ₹1,000 para actualizar su cuenta?
[Customer]: Sí, me comprometo a pagar ₹1,000.00 el día 26 de noviembre.
[Agent]: Excelente. Registro la promesa de pago por ₹1,000 para el 26 de noviembre. Le llegará la confirmación por correo.
[Customer]: Muchas gracias por la atención y la paciencia.`,
    call_summary: 'Interacción en español. Cliente reconoció el saldo pendiente de ₹3,200. Prometió abonar ₹1,000.00 el 26 de noviembre tras recibir fondos de su negocio.',
    customer_feedback: 'Positive tone. Appreciated customer support in his native language and clear instructions.',
    payment_status: 'Promised to Pay',
    promise_to_pay_date: '2024-11-26',
    promise_to_pay_amount: 1000.00,
    call_recording: 'https://actions.google.com/sounds/v1/speech/spanish_conversation.ogg',
  },
  {
    interaction_id: 3,
    customer_id: 103,
    call_datetime: '2024-11-18T16:45:00Z',
    call_status: 'Completed',
    language_used: 'Hindi',
    call_transcript: `[Agent]: Namaste, kya main Priya Sharma ji se baat kar raha hoon?
[Customer]: Haan, main Priya bol rahi hoon.
[Agent]: Priya ji, main loan services se baat kar raha hoon. Aapka remaining balance ₹850 pending hai jiska due date kal tha.
[Customer]: Haan, mujhe yaad hai. Maine net banking se abhi payment initiate kiya tha par server error aa raha tha.
[Agent]: Main aapko direct payment link SMS par bhej deta hoon. Kya aap aaj hi pura balance clear kar sakti hain?
[Customer]: Haan bilkul, link bhej dijiye, main aaj hi ₹850 clear kar dungi.
[Agent]: Bahut dhanyawad Priya ji. Link bhej diya gaya hai.`,
    call_summary: 'Customer was already attempting to pay via net banking but faced portal glitch. Agent sent direct instant payment link. Customer agreed to settle full ₹850.00.',
    customer_feedback: 'Customer was prompt and satisfied with agent providing alternative payment link immediately.',
    payment_status: 'Paid',
    promise_to_pay_date: '2024-11-18',
    promise_to_pay_amount: 850.00,
    call_recording: 'https://actions.google.com/sounds/v1/speech/hindi_prompt.ogg',
  },
  {
    interaction_id: 4,
    customer_id: 104,
    call_datetime: '2024-11-17T11:00:00Z',
    call_status: 'Completed',
    language_used: 'English',
    call_transcript: `[Agent]: Good morning Marcus, calling regarding loan account #104 with ₹6,200.75 balance.
[Customer]: Look, I already disputed the late fee charges with customer care last week! Why am I still getting calls?
[Agent]: I apologize for the inconvenience, Marcus. Let me pull up your dispute records... I see the fee review ticket #8821 is currently in progress.
[Customer]: Fine, but I am not making any payment until that ₹150 dispute is settled and deducted from my balance!
[Agent]: Understood. I will expedite ticket #8821 with the billing escalation team and put a temporary freeze on automated calls for 72 hours.
[Customer]: Thanks, do that.`,
    call_summary: 'Customer agitated regarding pending late fee dispute ticket #8821 (₹150). Refused payment until fee adjustment is reflected. Escalated to billing and placed 72-hr hold.',
    customer_feedback: 'Dissatisfied with repeat calls during ongoing dispute resolution. Escalation requested.',
    payment_status: 'Disputed',
    promise_to_pay_date: null,
    promise_to_pay_amount: null,
    call_recording: null,
  },
  {
    interaction_id: 5,
    customer_id: 101,
    call_datetime: '2024-11-10T09:15:00Z',
    call_status: 'No Answer',
    language_used: 'English',
    call_transcript: '[System]: Call placed to +1 (555) 234-8901. Rang 6 times. Voicemail beeped. Automated reminder message left regarding upcoming due date November 30.',
    call_summary: 'No answer. Automated courtesy reminder voicemail dropped.',
    customer_feedback: null,
    payment_status: 'Pending Review',
    promise_to_pay_date: null,
    promise_to_pay_amount: null,
    call_recording: null,
  },
  {
    interaction_id: 6,
    customer_id: 106,
    call_datetime: '2024-11-20T15:20:00Z',
    call_status: 'Completed',
    language_used: 'English',
    call_transcript: `[Agent]: Hello David, this is Maya following up on your installment plan for ₹2,750.25.
[Customer]: Hi Maya, I've got my schedule in front of me. Can we set up an auto-debit on the 1st of December for ₹1,200?
[Agent]: Certainly David! I've set the auto-debit authorization for ₹1,200 on December 1st, 2024.
[Customer]: Perfect, that works smoothly for me. Thanks Maya.`,
    call_summary: 'Customer scheduled auto-debit authorization of ₹1,200 on December 1st towards the ₹2,750.25 balance.',
    customer_feedback: 'Very proactive and appreciative of online scheduled debit options.',
    payment_status: 'Promised to Pay',
    promise_to_pay_date: '2024-12-01',
    promise_to_pay_amount: 1200.00,
    call_recording: 'https://actions.google.com/sounds/v1/speech/male_prompt.ogg',
  },
]
