-- 1. Create borrowers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    email VARCHAR(150),
    language VARCHAR(50),
    lending_date DATE,
    due_date DATE,
    outstanding_amount NUMERIC(12, 2) DEFAULT 0,
    principal_amount NUMERIC(12, 2) NOT NULL,
    interest_rate NUMERIC(5, 2) NOT NULL
);

-- 2. Create Agent Table
CREATE TABLE IF NOT EXISTS agent (
    interaction_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    call_datetime TIMESTAMP,
    call_status VARCHAR(30),
    language_used VARCHAR(50),
    call_transcript TEXT,
    call_summary TEXT,
    customer_feedback TEXT,
    payment_status VARCHAR(30),
    promise_to_pay_date DATE,
    promise_to_pay_amount NUMERIC(12, 2),
    call_recording TEXT,

    CONSTRAINT fk_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);

-- Supabase Auth manages accounts and passwords.
CREATE TABLE IF NOT EXISTS public.profiles (
 id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
 full_name TEXT NOT NULL DEFAULT '',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Read own profile" ON public.profiles;
CREATE POLICY "Read own profile" ON public.profiles FOR SELECT TO authenticated USING (id = (select auth.uid()));
GRANT SELECT ON public.profiles TO authenticated;
CREATE OR REPLACE FUNCTION public.handle_cashfree_signup()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
 INSERT INTO public.profiles (id, full_name)
 VALUES (new.id, coalesce(new.raw_user_meta_data ->> 'full_name', '')) ON CONFLICT (id) DO NOTHING;
 RETURN new;
END;
$$;
REVOKE ALL ON FUNCTION public.handle_cashfree_signup() FROM PUBLIC;
DROP TRIGGER IF EXISTS on_cashfree_signup ON auth.users;
CREATE TRIGGER on_cashfree_signup AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION public.handle_cashfree_signup();
INSERT INTO public.profiles (id, full_name) SELECT id, coalesce(raw_user_meta_data ->> 'full_name', '') FROM auth.users ON CONFLICT (id) DO NOTHING;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) DEFAULT auth.uid();
ALTER TABLE public.agent ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) DEFAULT auth.uid();
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public access to customers" ON public.customers;
DROP POLICY IF EXISTS "Allow public access to agent" ON public.agent;
DROP POLICY IF EXISTS "Own customers" ON public.customers;
DROP POLICY IF EXISTS "Own interactions" ON public.agent;
DROP POLICY IF EXISTS "Customer ownership guard" ON public.customers;
DROP POLICY IF EXISTS "Interaction ownership guard" ON public.agent;
CREATE POLICY "Own customers" ON public.customers FOR ALL TO authenticated USING (user_id = (select auth.uid())) WITH CHECK (user_id = (select auth.uid()));
CREATE POLICY "Customer ownership guard" ON public.customers AS RESTRICTIVE FOR ALL TO public USING (user_id = (select auth.uid())) WITH CHECK (user_id = (select auth.uid()));
CREATE POLICY "Own interactions" ON public.agent FOR ALL TO authenticated USING (user_id = (select auth.uid())) WITH CHECK (user_id = (select auth.uid()) AND EXISTS (SELECT 1 FROM public.customers c WHERE c.customer_id = agent.customer_id AND c.user_id = (select auth.uid())));
CREATE POLICY "Interaction ownership guard" ON public.agent AS RESTRICTIVE FOR ALL TO public USING (user_id = (select auth.uid())) WITH CHECK (user_id = (select auth.uid()) AND EXISTS (SELECT 1 FROM public.customers c WHERE c.customer_id = agent.customer_id AND c.user_id = (select auth.uid())));
GRANT SELECT, INSERT, UPDATE, DELETE ON public.customers, public.agent TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.customers_customer_id_seq, public.agent_interaction_id_seq TO authenticated;
CREATE INDEX IF NOT EXISTS customers_user_id_idx ON public.customers(user_id);
CREATE INDEX IF NOT EXISTS agent_user_id_idx ON public.agent(user_id);
-- Existing rows with NULL user_id are hidden. Assign them explicitly to the
-- correct auth.users.id when migrating an existing portfolio.
