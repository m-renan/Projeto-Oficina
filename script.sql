-- PROJETO: Sistema de Gerenciamento de Oficina Mecânica
-- SGBD: PostgreSQL

DROP TABLE IF EXISTS historico_os CASCADE;
DROP TABLE IF EXISTS itens_os CASCADE;
DROP TABLE IF EXISTS ordens_servico CASCADE;
DROP TABLE IF EXISTS servicos CASCADE;
DROP TABLE IF EXISTS veiculos CASCADE;
DROP TABLE IF EXISTS clientes CASCADE;

CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    telefone VARCHAR(20) NOT NULL,
    email VARCHAR(100)
);

CREATE TABLE veiculos (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    marca VARCHAR(50) NOT NULL,
    modelo VARCHAR(50) NOT NULL,
    placa VARCHAR(10) UNIQUE NOT NULL
);

CREATE TABLE servicos (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(100) NOT NULL,
    preco NUMERIC(10,2) NOT NULL CHECK (preco >= 0)
);

CREATE TABLE ordens_servico (
    id SERIAL PRIMARY KEY,
    veiculo_id INTEGER NOT NULL REFERENCES veiculos(id),
    descricao_problema TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ABERTA'
        CHECK (status IN ('ABERTA', 'FINALIZADA', 'CANCELADA')),
    total NUMERIC(10,2) NOT NULL DEFAULT 0,
    criada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE itens_os (
    id SERIAL PRIMARY KEY,
    ordem_id INTEGER NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
    servico_id INTEGER NOT NULL REFERENCES servicos(id),
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    valor_unitario NUMERIC(10,2) NOT NULL CHECK (valor_unitario >= 0)
);

CREATE TABLE historico_os (
    id SERIAL PRIMARY KEY,
    ordem_id INTEGER NOT NULL REFERENCES ordens_servico(id),
    status_anterior VARCHAR(20),
    status_novo VARCHAR(20) NOT NULL,
    alterado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO servicos (descricao, preco) VALUES
('Troca de óleo', 80.00),
('Alinhamento e balanceamento', 120.00),
('Revisão básica', 250.00),
('Troca de pastilhas de freio', 180.00);

-- FUNCTION: calcula e retorna o valor total de uma ordem.
CREATE OR REPLACE FUNCTION fn_total_os(p_ordem_id INTEGER)
RETURNS NUMERIC(10,2)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total NUMERIC(10,2);
BEGIN
    SELECT COALESCE(SUM(quantidade * valor_unitario), 0)
      INTO v_total
      FROM itens_os
     WHERE ordem_id = p_ordem_id;

    RETURN v_total;
END;
$$;

-- PROCEDURE: cria a ordem e seu item em etapas.
-- A aplicação inicia a transação e confirma (COMMIT) ou desfaz (ROLLBACK).
CREATE OR REPLACE PROCEDURE sp_criar_os(
    IN p_veiculo_id INTEGER,
    IN p_problema TEXT,
    IN p_servico_id INTEGER,
    IN p_quantidade INTEGER,
    OUT p_ordem_id INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_preco NUMERIC(10,2);
BEGIN
    IF p_quantidade <= 0 THEN
        RAISE EXCEPTION 'A quantidade deve ser maior que zero.';
    END IF;

    SELECT preco INTO v_preco
      FROM servicos
     WHERE id = p_servico_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Serviço não encontrado.';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM veiculos WHERE id = p_veiculo_id) THEN
        RAISE EXCEPTION 'Veículo não encontrado.';
    END IF;

    INSERT INTO ordens_servico (veiculo_id, descricao_problema)
    VALUES (p_veiculo_id, p_problema)
    RETURNING id INTO p_ordem_id;

    INSERT INTO itens_os (ordem_id, servico_id, quantidade, valor_unitario)
    VALUES (p_ordem_id, p_servico_id, p_quantidade, v_preco);

    UPDATE ordens_servico
       SET total = fn_total_os(p_ordem_id)
     WHERE id = p_ordem_id;
END;
$$;

-- PROCEDURE: finaliza uma ordem aberta.
CREATE OR REPLACE PROCEDURE sp_finalizar_os(IN p_ordem_id INTEGER)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE ordens_servico
       SET status = 'FINALIZADA',
           total = fn_total_os(p_ordem_id)
     WHERE id = p_ordem_id
       AND status = 'ABERTA';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Ordem não encontrada ou não está aberta.';
    END IF;
END;
$$;

-- TRIGGER: registra automaticamente cada mudança de status.
CREATE OR REPLACE FUNCTION fn_auditar_status_os()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO historico_os (ordem_id, status_anterior, status_novo)
        VALUES (NEW.id, OLD.status, NEW.status);
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_historico_status_os
AFTER UPDATE OF status ON ordens_servico
FOR EACH ROW
EXECUTE FUNCTION fn_auditar_status_os();

-- Dados opcionais para teste:
-- INSERT INTO clientes (nome, telefone, email)
-- VALUES ('Maria Silva', '(89) 99999-0000', 'maria@email.com');
-- INSERT INTO veiculos (cliente_id, marca, modelo, placa)
-- VALUES (1, 'Fiat', 'Palio', 'ABC1D23');
-- BEGIN;
-- CALL sp_criar_os(1, 'Barulho no motor', 1, 2, NULL);
-- COMMIT;
-- SELECT fn_total_os(1);
-- CALL sp_finalizar_os(1);
