#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Café Telegram bot

LIMITE_FETCH = 50

excluir = [u'pagou', u'para', u'o', u'a', u'à', u'ao', u'e']
DIAS_SEMANA = [u'Dom', u'Seg', u'Ter', u'Qua', u'Qui', u'Sex', u'Sáb']

from flask import Flask, request
import sqlite3
import telegram
import time

from local_config import *

CERT     = 'src/server.crt'
CERT_KEY = 'src/server.key'

bot = telegram.Bot(TOKEN)
app = Flask(__name__)
context = (CERT, CERT_KEY)

db = sqlite3.connect('vol/cafe.db', check_same_thread = False)

def formata_nomes(id_grupo, nomes):
    pts = {}
    db_conn = db.cursor()

    for n in nomes:
        db_conn.execute('SELECT pontos FROM pessoa WHERE id_grupo = ? AND nome = ?', (id_grupo, n))
        row = db_conn.fetchone()
        if not row:
            pts[n] = '0'
        else:
            pts[n] = str(row[0])
            if row[0] > 0:
                pts[n] = u'+' + pts[n]

    saida = []
    for item in nomes:
        saida.append(item + u' (' + pts[item] + u')')

    rsp = u', '.join(saida[:-2])
    if len(nomes) >= 3:
        rsp = rsp + u', '
    rsp = rsp + u' e '.join(saida[-2:])

    return rsp

def quem_paga(id_grupo):
    rsp = lista_nomes('SELECT nome, pontos, ativo FROM pessoa WHERE id_grupo = ? AND pontos <= 0 AND ativo = "S" ORDER BY pontos, RANDOM() LIMIT 50', id_grupo, separador = ', ')
    return u'Próximos: ' + rsp + '.'

def limpa_str(frase):
    retorno = []
    for item in frase:
        if not item in excluir:
            retorno.append(u''.join(c for c in item if c not in '.,:!?'))
    return retorno

def set_pontos(id_grupo, nome, pontos):
    db_conn = db.cursor()
    db_conn.execute('SELECT pontos, id FROM pessoa WHERE id_grupo = ? AND nome = ?', (id_grupo, nome))
    row = db_conn.fetchone()
    if not row:
        db_conn.execute("INSERT INTO pessoa (id_grupo, nome, pontos, ativo, last_access) VALUES (?, ?, ?, ?, DATETIME('now'))", (id_grupo, nome, pontos, 'S'))
        id = db_conn.lastrowid
    else:
        db_conn.execute("UPDATE pessoa SET pontos = ?, ativo = ?, last_access = DATETIME('now') WHERE id_grupo = ? AND nome = ?", (pontos, 'S', id_grupo, nome))
        id = row[1]
    db.commit()
    db_conn.close()
    return id

def get_pontos(id_grupo, nome):
    db_conn = db.cursor()
    db_conn.execute('SELECT pontos FROM pessoa WHERE id_grupo = ? AND nome = ?', (id_grupo, nome))
    row = db_conn.fetchone()
    if not row:
        return 0
    else:
        return row[0]

def get_pessoa_id(id_grupo, nome):
    db_conn = db.cursor()
    db_conn.execute('SELECT id FROM pessoa WHERE id_grupo = ? AND nome = ?', (id_grupo, nome))
    row = db_conn.fetchone()
    if not row:
        return None
    else:
        return row[0]

def lista_nomes(sql, id_grupo, destaca_menor = True, separador = "\n", destaca_inativo = True, mostra_pontos = True, tipo_min = 'A'):
    rsp = u''
    db_conn = db.cursor()

    if destaca_menor:
        if tipo_min == 'A':
            db_conn.execute("SELECT MIN(pontos) FROM pessoa WHERE ativo = 'S' AND id_grupo = ?", (id_grupo,))
        elif tipo_min == 'I':
            db_conn.execute("SELECT MIN(pontos) FROM pessoa WHERE ativo = 'N' AND id_grupo = ?", (id_grupo,))
        else:
            db_conn.execute("SELECT MIN(pontos) FROM pessoa WHERE ativo <> 'X' AND id_grupo = ?", (id_grupo,))
        row = db_conn.fetchone()
        min_pts = row[0]

    db_conn.execute(sql, (id_grupo,))
    rows = db_conn.fetchmany(size = LIMITE_FETCH)
    for i in rows:

        if destaca_menor and i[1] == min_pts:
            rsp = rsp + '<b>' + i[0] + u'</b>'
        else:
            rsp = rsp + i[0]

        if mostra_pontos:
            pts = str(i[1])
            if i[1] > 0:
                pts = u'+' + pts
            rsp = rsp + u' (' + pts + u')'

        if destaca_inativo and i[2] == 'N':
            rsp = rsp + u' *'

        if not i is rows[-1]:
            rsp = rsp + separador

    return rsp

@app.route('/')
def hello():
    return u'Bot do café!'

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    update = telegram.update.Update.de_json(request.get_json(force=True), bot)

    if not update.message:
      return 'OK'

    if not update.message.text:
      return 'OK'

    # determina o grupo
    db_conn = db.cursor()
    db_conn.execute("SELECT id FROM grupo WHERE chat_id = ?", (update.message.chat.id,))
    row = db_conn.fetchone()
    if not row:
        db_conn.execute("INSERT INTO grupo (chat_id, last_access) VALUES (?, DATETIME('now'))", (update.message.chat.id,))
        id_grupo = db_conn.lastrowid
    else:
        id_grupo = int(row[0])
        db_conn.execute("UPDATE grupo SET last_access = DATETIME('now') WHERE id = ?", (id_grupo,))

    db.commit()
    db_conn.close()

    if len(update.message.text) > 200:
      rsp = u"Sua mensagem é muito longa. Quebre em mais de um lançamento, caso esteja correta."
      bot.sendMessage(chat_id=update.message.chat_id, text=rsp, parse_mode='HTML')
      return 'OK'

    # tratamento de mensagens
    if update.message.text.startswith('/'):
        tokens = update.message.text.split(' ')
        rsp = None

        if len(tokens) > 20:
          rsp = u"Sua mensagem é muito longa. Quebre em mais de um lançamento, caso esteja correta."
          tokens[0] = u''

        # remove token_id de chat de grupo
        split_token = tokens[0].split('@')
        if len(split_token) > 1 and split_token[1] == BOT_NAME:
            tokens[0] = split_token[0]

        # normaliza os nomes
        for i in range(1, len(tokens)):
            if tokens[i] not in excluir:
                tokens[i] = tokens[i].capitalize()

        #
        # /quem
        #

        if tokens[0] == u'/quem':
            rsp = quem_paga(id_grupo)

        #
        # /pagou <nome> [para] <nome>[,] <nome> [e] <nome>[.]
        #

        elif tokens[0] == u'/pagou':
            tokens = limpa_str(tokens)

            # remove duplicados e vazios, e mantem a ordem
            # list(set(tokens)) nao mantem a ordem original
            tokens_unicos = []
            for i in tokens:
                if (i not in tokens_unicos) and (len(i) > 0):
                    tokens_unicos.append(i)
            tokens = tokens_unicos

            if len(tokens) <= 2:
                rsp = u"Indique quem deve pagar.\nEx.: /pagou João a Maria"
            else:
                rsp = formata_nomes(id_grupo, (tokens[1],)) + ' pagou a ' + formata_nomes(id_grupo, tokens[2:]) + '.'

                # pagamento
                ptos = get_pontos(id_grupo, tokens[1])
                id = set_pontos(id_grupo, tokens[1], ptos + len(tokens) - 2)
                db_conn = db.cursor()
                db_conn.execute("SELECT MAX(id) FROM pgto WHERE id_grupo = ?", (id_grupo,))
                row = db_conn.fetchone()
                if row[0] is None:
                    id_pgto = 1
                else:
                    id_pgto = int(row[0]) + 1
                db_conn.execute("INSERT INTO pgto (id, id_grupo, pessoa, data) VALUES (?, ?, ?, DATETIME('now'))", (id_pgto, id_grupo, id))
                db_conn.close()

                # detalhes do pagamento
                for i in tokens[2:]:
                    ptos = get_pontos(id_grupo, i)
                    id_recebeu = set_pontos(id_grupo, i, ptos - 1)
                    db_conn = db.cursor()
                    db_conn.execute("SELECT MAX(id) FROM det_pgto WHERE id_grupo = ?", (id_grupo,))
                    row = db_conn.fetchone()
                    if row[0] is None:
                        id = 1
                    else:
                        id = int(row[0]) + 1
                    db_conn.execute("INSERT INTO det_pgto (id, id_grupo, pgto, recebeu) VALUES (?, ?, ?, ?);", (id, id_grupo, id_pgto, id_recebeu))
                    db_conn.close()

                db.commit()
                rsp = rsp + u"\n\nNova pontuação: " + formata_nomes(id_grupo, (tokens[1:])) + '.'
                rsp = rsp + "\n\n" + quem_paga(id_grupo)

        #
        # /inative <nome>
        #

        elif tokens[0] == u'/inative':
            if len(tokens) < 2:
                rsp = u"Retira nome da lista de pagamentos.\nEx.: /inative João"
            else:
                db_conn = db.cursor()
                db_conn.execute("UPDATE pessoa SET ativo = 'N' WHERE id_grupo = ? AND nome = ?", (id_grupo, tokens[1]))
                db.commit()
                db_conn.close()
                if db_conn.rowcount == 0:
                    rsp = u'Não encontrei ninguém com este nome.'
                else:
                    rsp = u'<b>' + tokens[1] + u"</b> não participará por enquanto.\n\n" + quem_paga(id_grupo)

        #
        # /reative <nome>
        #

        elif tokens[0] == u'/reative':
            if len(tokens) < 2:
                rsp = u"Reativa nome para lista de pagamentos.\nEx.: /reative João"
            else:
                db_conn = db.cursor()
                db_conn.execute("UPDATE pessoa SET ativo = 'S' WHERE id_grupo = ? AND nome = ?", (id_grupo, tokens[1]))
                db.commit()
                db_conn.close()
                if db_conn.rowcount == 0:
                    rsp = u'Não encontrei ninguém com este nome.'
                else:
                    rsp = u'<b>' + tokens[1] + u"</b> volta a participar.\n\n" + quem_paga(id_grupo)

        #
        # /inativos
        #

        elif tokens[0] == u'/inativos':
            rsp = lista_nomes('SELECT nome, pontos, ativo FROM pessoa WHERE id_grupo = ? AND ativo = "N" AND pontos != 0 ORDER BY nome LIMIT 50', id_grupo, separador = ', ', destaca_inativo = False, tipo_min = 'I')
            rsp = u'Inativos: ' + rsp + '.'

        #
        # /pagamentos
        #

        elif tokens[0] == u'/pagamentos':
            rsp = u''
            db_conn = db.cursor()
            db_conn.execute("SELECT a.id, strftime('%w %d/%m', a.data), b.nome FROM pgto a, pessoa b WHERE a.pessoa = b.id AND a.id_grupo = ? AND data >= DATE('now', '-14 days') ORDER BY a.data DESC LIMIT 50", (id_grupo,))
            rows = db_conn.fetchmany(size = LIMITE_FETCH)
            for i in rows:
                quando = DIAS_SEMANA[int(i[1][0])] + i[1][1:]
                rsp = rsp + str(i[0]) + u') ' + quando + ': ' + i[2] + ' pagou a '
                db_conn2 = db.cursor()
                db_conn2.execute('SELECT b.nome FROM det_pgto a, pessoa b WHERE a.recebeu = b.id AND a.id_grupo = ? AND b.id_grupo = ? AND a.pgto = ? LIMIT 50', (id_grupo, id_grupo, i[0]))
                nomes = []
                for j in db_conn2.fetchmany(size = LIMITE_FETCH):
                    nomes.append(j[0])
                rsp = rsp + u', '.join(nomes[:-2])
                if len(nomes) >= 3:
                    rsp = rsp + u', '
                rsp = rsp + u' e '.join(nomes[-2:]) + ".\n"

        #
        # /auditar <nome>
        #

        elif tokens[0] == u'/auditar':
            if len(tokens) < 2:
                rsp = u"Indique quem será auditado.\nEx.: /auditar João"
            else:
                id_pessoa = get_pessoa_id(id_grupo, tokens[1])
                if not id_pessoa:
                    rsp = u'Não encontrei alguém com este nome.'
                else:
                    rsp = u''
                    db_conn = db.cursor()

                    # lista todos os pagamentos ligados à pessoa auditada
                    db_conn.execute("SELECT a.id, strftime('%w %d/%m', a.data), b.nome FROM pgto a, pessoa b WHERE a.pessoa = b.id AND a.id_grupo = ? AND a.id IN (SELECT id FROM pgto WHERE id_grupo = ? AND pessoa = ? UNION ALL SELECT pgto FROM det_pgto WHERE id_grupo = ? AND recebeu = ?) ORDER BY a.data DESC LIMIT 20", (id_grupo, id_grupo, id_pessoa, id_grupo, id_pessoa))
                    rows = db_conn.fetchmany(size = LIMITE_FETCH)
                    for i in rows:
                        quando = DIAS_SEMANA[int(i[1][0])] + i[1][1:]
                        if tokens[1] == i[2]:
                            n = '<b>' + i[2] + '</b>'
                        else:
                            n = i[2]
                        rsp = rsp + str(i[0]) + u') ' + quando + ': ' + n + ' pagou a '
                        db_conn2 = db.cursor()
                        db_conn2.execute('SELECT b.nome FROM det_pgto a, pessoa b WHERE a.recebeu = b.id AND a.id_grupo = ? AND b.id_grupo = ? AND a.pgto = ? LIMIT 50', (id_grupo, id_grupo, i[0]))
                        nomes = []
                        for j in db_conn2.fetchmany(size = LIMITE_FETCH):
                            if j[0] == tokens[1]:
                                n = '<b>' + j[0] + '</b>'
                            else:
                                n = j[0]
                            nomes.append(n)
                        rsp = rsp + u', '.join(nomes[:-2])
                        if len(nomes) >= 3:
                            rsp = rsp + u', '
                        rsp = rsp + u' e '.join(nomes[-2:]) + ".\n"

        #
        # /apague <número>
        #

        elif tokens[0] == u'/apague':
            if len(tokens) < 2:
                rsp = u"Indique qual pagamento deve ser apagado, após listar os pagamentos recentes com /pagamentos.\nEx.: /apague 105"
            else:
                db_conn = db.cursor()
                db_conn.execute('SELECT b.nome FROM det_pgto a, pessoa b WHERE a.recebeu = b.id AND a.id_grupo = ? AND b.id_grupo = ? AND a.pgto = ? LIMIT 50', (id_grupo, id_grupo, tokens[1]))
                nomes = db_conn.fetchmany(size = LIMITE_FETCH)
                for i in nomes:
                    ptos = get_pontos(id_grupo, i[0])
                    set_pontos(id_grupo, i[0], ptos + 1)
                db_conn.execute('SELECT a.nome FROM pessoa a, pgto b WHERE a.id = b.pessoa AND b.id_grupo = ? AND b.id = ?', (id_grupo, tokens[1]))
                row = db_conn.fetchone()
                if not row:
                    rsp = u'Este pagamento não existe.'
                else:
                    ptos = get_pontos(id_grupo, row[0])
                    set_pontos(id_grupo, row[0], ptos - len(nomes))
                    db_conn.execute('DELETE FROM det_pgto WHERE pgto = ? AND id_grupo = ?', (tokens[1], id_grupo))
                    db_conn.execute('DELETE FROM pgto WHERE id = ? AND id_grupo = ?', (tokens[1], id_grupo))
                    db.commit()
                    db_conn.close()
                    rsp = u'Pagamento ' + str(tokens[1]) + " apagado.\n\n" + quem_paga(id_grupo)

        #
        # /mescle
        #

        elif tokens[0] == u'/mescle':
            if len(tokens) < 3:
                rsp = u"Indique quais usuários devem ser mesclados.\nEx.: /mescle João Joao"
            else:
                id_a = get_pessoa_id(id_grupo, tokens[1])
                id_b = get_pessoa_id(id_grupo, tokens[2])
                if not id_a:
                    rsp = u'Não há pessoa com nome "' + tokens[1]
                elif not id_b:
                    rsp = u'Não há pessoa com nome "' + tokens[2]
                else:
                    db_conn = db.cursor()
                    db_conn.execute('UPDATE det_pgto SET recebeu = ? WHERE recebeu = ? AND id_grupo = ?', (id_a, id_b, id_grupo))
                    db_conn.execute('UPDATE pgto SET pessoa = ? WHERE pessoa = ? AND id_grupo = ?', (id_a, id_b, id_grupo))
                    ptos_a = get_pontos(id_grupo, tokens[1])
                    ptos_b = get_pontos(id_grupo, tokens[2])
                    db_conn.execute('UPDATE pessoa SET pontos = ? WHERE id = ? AND id_grupo = ?', (ptos_a + ptos_b, id_a, id_grupo))
                    db_conn.execute('DELETE FROM pessoa WHERE id = ? AND id_grupo = ?', (id_b, id_grupo))
                    db.commit()
                    db_conn.close()
                    rsp = u"Usuário \"" + tokens[2] + u"\" mesclado com \"" + tokens[1] + "\".\n\n" + quem_paga(id_grupo)

        #
        # /nomes
        #

        elif tokens[0] == u'/nomes':
            rsp = lista_nomes('SELECT nome, pontos, ativo FROM pessoa WHERE id_grupo = ? AND ativo = "S" ORDER BY nome LIMIT 50', id_grupo)

        #
        # /todos
        #

        elif tokens[0] == u'/todos':
            rsp = lista_nomes('SELECT nome, pontos, ativo FROM pessoa WHERE id_grupo = ? AND ativo <> "X" ORDER BY nome LIMIT 50', id_grupo, tipo_min = 'T')

        #
        # /pontos
        #

        elif tokens[0] == u'/pontos':
            rsp = lista_nomes('SELECT nome, pontos, ativo FROM pessoa WHERE id_grupo = ? AND ativo = "S" ORDER BY pontos, nome LIMIT 50', id_grupo)

        #
        # /zerados
        #

        elif tokens[0] == u'/zerados':
            rsp = lista_nomes('SELECT nome, pontos, ativo FROM pessoa WHERE id_grupo = ? AND pontos = 0 AND ativo = "S" ORDER BY nome LIMIT 50', id_grupo, separador = ', ', mostra_pontos = False)
            rsp = u'Zerados: ' + rsp + '.'

        #
        # start
        #

        elif tokens[0] == u'/start':
            rsp = u"Olá! Eu sou o bot do café.\nLance um pagamento com /pagou (como em \"/pagou João a Maria e José\"), e veja quem é o próximo a pagar com /quem. Digite / (barra) para listar todos os comandos."

        if rsp:
            bot.sendMessage(chat_id=update.message.chat_id, text=rsp, parse_mode='HTML')

    return 'OK'

def setWebhook():
    bot.setWebhook(url='https://%s:%s/%s' % (HOST, PORT, TOKEN),
                   certificate=open(CERT, 'rb'))

if __name__ == '__main__':
    setWebhook()
    time.sleep(1)
    app.run(host='0.0.0.0',
            port=PORT,
            ssl_context=context,
            debug=True)
