"""
Sistema de Gerenciamento de Oficina Mecânica
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import psycopg2

# Ajuste os dados para os do seu PostgreSQL.
DB = {
    "host": "localhost",
    "database": "oficina_db",
    "user": "postgres",
    "password": "",
    "port": "5432"
}

def conectar():
    return psycopg2.connect(**DB)

class OficinaApp:
    def __init__(self, root):
        self.root = root
        root.title("Oficina Mecânica - Sistema de Gestão")
        root.geometry("850x560")
        root.minsize(750, 500)

        topo = ttk.Frame(root, padding=12)
        topo.pack(fill="x")
        ttk.Label(topo, text="OFICINA MECÂNICA", font=("Arial", 18, "bold")).pack(side="left")
        ttk.Button(topo, text="Atualizar lista", command=self.listar).pack(side="right")
        ttk.Button(topo, text="Finalizar OS", command=self.finalizar_os).pack(side="right", padx=5)
        ttk.Button(topo, text="Abrir OS (Procedure)", command=self.abrir_os).pack(side="right", padx=5)

        form = ttk.LabelFrame(root, text="Cadastro de cliente", padding=12)
        form.pack(fill="x", padx=12)
        self.nome = tk.StringVar()
        self.telefone = tk.StringVar()
        self.email = tk.StringVar()
        ttk.Label(form, text="Nome").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.nome, width=32).grid(row=0, column=1, padx=5, pady=4)
        ttk.Label(form, text="Telefone").grid(row=0, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.telefone, width=20).grid(row=0, column=3, padx=5, pady=4)
        ttk.Label(form, text="E-mail").grid(row=1, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.email, width=32).grid(row=1, column=1, padx=5, pady=4)
        ttk.Button(form, text="Cadastrar", command=self.cadastrar).grid(row=1, column=2, padx=5)
        ttk.Button(form, text="Editar selecionado", command=self.editar).grid(row=1, column=3, padx=5)

        lista = ttk.LabelFrame(root, text="Clientes cadastrados (CRUD)", padding=10)
        lista.pack(fill="both", expand=True, padx=12, pady=12)
        colunas = ("id", "nome", "telefone", "email")
        self.tree = ttk.Treeview(lista, columns=colunas, show="headings")
        for col, titulo, largura in [
            ("id", "ID", 55), ("nome", "Nome", 250),
            ("telefone", "Telefone", 150), ("email", "E-mail", 300)
        ]:
            self.tree.heading(col, text=titulo)
            self.tree.column(col, width=largura)
        self.tree.pack(fill="both", expand=True)
        botoes = ttk.Frame(lista)
        botoes.pack(fill="x", pady=(8, 0))
        ttk.Button(botoes, text="Excluir selecionado", command=self.excluir).pack(side="left")
        ttk.Button(botoes, text="Limpar campos", command=self.limpar).pack(side="left", padx=8)

        rodape = ttk.Label(root, text="PostgreSQL • CRUD • Procedure • Function • Trigger",
                           foreground="#555")
        rodape.pack(pady=(0, 8))
        self.listar()

    def executar(self, sql, valores=(), fetch=False):
        conn = conectar()
        try:
            cur = conn.cursor()
            cur.execute(sql, valores)
            resultado = cur.fetchall() if fetch else None
            conn.commit()
            cur.close()
            return resultado
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def listar(self):
        try:
            dados = self.executar(
                "SELECT id, nome, telefone, COALESCE(email, '') FROM clientes ORDER BY id",
                fetch=True
            )
            self.tree.delete(*self.tree.get_children())
            for linha in dados:
                self.tree.insert("", "end", values=linha)
        except Exception as e:
            messagebox.showerror("Erro de conexão", f"Confira o PostgreSQL e os dados de conexão.\n\n{e}")

    def cadastrar(self):
        nome = self.nome.get().strip()
        telefone = self.telefone.get().strip()
        email = self.email.get().strip()
        if not nome or not telefone:
            messagebox.showwarning("Atenção", "Preencha nome e telefone.")
            return
        try:
            self.executar(
                "INSERT INTO clientes (nome, telefone, email) VALUES (%s, %s, %s)",
                (nome, telefone, email or None)
            )
            messagebox.showinfo("Sucesso", "Cliente cadastrado!")
            self.limpar()
            self.listar()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def editar(self):
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning("Atenção", "Selecione um cliente na lista.")
            return
        cliente_id = self.tree.item(selecionado[0], "values")[0]
        if not self.nome.get().strip() or not self.telefone.get().strip():
            messagebox.showwarning("Atenção", "Informe nome e telefone para editar.")
            return
        try:
            self.executar(
                "UPDATE clientes SET nome=%s, telefone=%s, email=%s WHERE id=%s",
                (self.nome.get().strip(), self.telefone.get().strip(),
                 self.email.get().strip() or None, cliente_id)
            )
            messagebox.showinfo("Sucesso", "Cliente atualizado!")
            self.limpar()
            self.listar()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def excluir(self):
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning("Atenção", "Selecione um cliente na lista.")
            return
        cliente_id = self.tree.item(selecionado[0], "values")[0]
        if not messagebox.askyesno("Confirmar", "Deseja excluir o cliente selecionado?"):
            return
        try:
            self.executar("DELETE FROM clientes WHERE id=%s", (cliente_id,))
            messagebox.showinfo("Sucesso", "Cliente excluído!")
            self.listar()
        except Exception as e:
            messagebox.showerror("Não foi possível excluir",
                                 "O cliente pode estar relacionado a um veículo.\n\n" + str(e))


    def abrir_os(self):
        """Chama a Procedure e confirma/desfaz a transação."""
        veiculo_id = simpledialog.askinteger("Nova ordem", "ID do veículo:")
        if veiculo_id is None:
            return
        problema = simpledialog.askstring("Nova ordem", "Descreva o problema:")
        if not problema:
            return
        servico_id = simpledialog.askinteger("Nova ordem", "ID do serviço:")
        if servico_id is None:
            return
        quantidade = simpledialog.askinteger("Nova ordem", "Quantidade:", minvalue=1)
        if quantidade is None:
            return

        conn = None
        try:
            conn = conectar()
            conn.autocommit = False
            cur = conn.cursor()
            cur.execute(
                "CALL sp_criar_os(%s, %s, %s, %s, NULL)",
                (veiculo_id, problema, servico_id, quantidade)
            )
            ordem_id = cur.fetchone()[0]
            conn.commit()
            messagebox.showinfo("Ordem criada",
                                f"Ordem de serviço #{ordem_id} criada com sucesso!")
        except Exception as e:
            if conn:
                conn.rollback()
            messagebox.showerror("Erro ao criar ordem",
                                 f"A transação foi desfeita (ROLLBACK).\n\n{e}")
        finally:
            if conn:
                conn.close()

    def finalizar_os(self):
        ordem_id = simpledialog.askinteger("Finalizar ordem", "ID da ordem de serviço:")
        if ordem_id is None:
            return
        conn = None
        try:
            conn = conectar()
            conn.autocommit = False
            cur = conn.cursor()
            cur.execute("CALL sp_finalizar_os(%s)", (ordem_id,))
            conn.commit()
            messagebox.showinfo("Sucesso",
                                "Ordem finalizada. O Trigger registrou a alteração no histórico.")
        except Exception as e:
            if conn:
                conn.rollback()
            messagebox.showerror("Erro", f"A transação foi desfeita (ROLLBACK).\n\n{e}")
        finally:
            if conn:
                conn.close()

    def limpar(self):
        self.nome.set("")
        self.telefone.set("")
        self.email.set("")

if __name__ == "__main__":
    janela = tk.Tk()
    app = OficinaApp(janela)
    janela.mainloop()
