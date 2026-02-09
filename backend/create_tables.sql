-- Create User table
CREATE TABLE IF NOT EXISTS api_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) UNIQUE NOT NULL,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    email VARCHAR(254) UNIQUE NOT NULL,
    profile_picture TEXT
);

-- Create UserChat table
CREATE TABLE IF NOT EXISTS api_userchat (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    messages JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    user_id UUID NOT NULL REFERENCES api_user(id) ON DELETE CASCADE
);

-- Create auth token table
CREATE TABLE IF NOT EXISTS authtoken_token (
    key VARCHAR(40) PRIMARY KEY,
    created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    user_id UUID NOT NULL UNIQUE REFERENCES api_user(id) ON DELETE CASCADE
);

-- Create django migrations table
CREATE TABLE IF NOT EXISTS django_migrations (
    id SERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Insert migration records
INSERT INTO django_migrations (app, name) VALUES 
('api', '0001_initial'),
('api', '0002_titanic_user_alter_statedata_income_and_more')
ON CONFLICT DO NOTHING;