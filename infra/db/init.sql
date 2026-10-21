-- Banco principal (rota) já é criado pela imagem; aqui criamos o de testes.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE DATABASE rota_teste;
\c rota_teste
CREATE EXTENSION IF NOT EXISTS postgis;
