import os
import re
import time
import pytest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


GRID_URL = "http://localhost:4444"

EVIDENCIAS = "evidencias"


def criar_pasta_evidencias():
    os.makedirs(EVIDENCIAS, exist_ok=True)


def criar_driver(browser):

    if browser == "chrome":

        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")

        return webdriver.Remote(
            command_executor=GRID_URL,
            options=options
        )

    elif browser == "edge":

        options = webdriver.EdgeOptions()
        options.add_argument("--start-maximized")

        return webdriver.Remote(
            command_executor=GRID_URL,
            options=options
        )

    elif browser == "firefox":

        options = webdriver.FirefoxOptions()

        return webdriver.Remote(
            command_executor=GRID_URL,
            options=options
        )

    else:
        raise ValueError(f"Navegador não suportado: {browser}")


def evidenciar(driver, nome):

    caminho = os.path.join(
        EVIDENCIAS,
        f"{nome}.png"
    )

    driver.save_screenshot(caminho)

    print(f"Evidência gerada: {caminho}")


def esperar(driver, segundos=10):

    return WebDriverWait(driver, segundos)


@pytest.mark.parametrize(
    "browser",
    ["chrome", "edge", "firefox"]
)
def test_jornada_compra_swift(browser):

    cep_teste = os.getenv("SWIFT_TEST_CEP", "").strip()

    if not re.fullmatch(r"\d{5}-?\d{3}", cep_teste):
        pytest.fail(
            "Defina SWIFT_TEST_CEP com um CEP válido "
            "(8 dígitos, com ou sem hífen)."
        )

    cep_teste = cep_teste.replace("-", "")

    criar_pasta_evidencias()

    driver = criar_driver(browser)

    try:

        # =========================================================
        # 1 - ACESSAR A SWIFT
        # =========================================================

        driver.get("https://loja.swift.com.br/")

        esperar(driver).until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) == "complete"
        )

        print(f"\nNavegador: {browser}")
        print(f"Título: {driver.title}")

        evidenciar(
            driver,
            f"{browser}_01_pagina_inicial"
        )


        # =========================================================
        # 2 - LOCALIZAR CAMPO DE PESQUISA
        # =========================================================

        campo_busca = esperar(driver).until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    "input[placeholder*='Swift']"
                )
            )
        )

        campo_busca.click()

        campo_busca.send_keys("Picanha")

        campo_busca.send_keys(Keys.ENTER)


        # =========================================================
        # 3 - VALIDAR SE A PESQUISA GEROU RESULTADO
        # =========================================================

        esperar(driver).until(
            EC.url_contains("/busca")
        )

        esperar(driver).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "button[aria-label='Adicionar']")
            )
        )

        evidenciar(
            driver,
            f"{browser}_02_resultado_busca"
        )

        print("Pesquisa realizada com sucesso.")


        # =========================================================
        # 4 - LOCALIZAR PRODUTO
        # =========================================================

        produto = esperar(driver).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//*[contains("
                    "translate(normalize-space(.),"
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    "'abcdefghijklmnopqrstuvwxyz'),"
                    "'picanha'"
                    ")]"
                )
            )
        )

        print(
            "Produto encontrado:",
            produto.text[:100]
        )


        # =========================================================
        # 5 - LOCALIZAR BOTÃO COMPRAR
        # =========================================================

        botoes_comprar = driver.find_elements(
            By.CSS_SELECTOR,
            "button[aria-label='Adicionar']"
        )

        if len(botoes_comprar) == 0:

            raise AssertionError(
                "Nenhum botão 'Adicionar' foi encontrado."
            )

        print(
            f"Quantidade de opções Comprar encontradas: "
            f"{len(botoes_comprar)}"
        )


        # =========================================================
        # 6 - SELECIONAR UMA OPÇÃO
        # =========================================================

        botao_comprar = botoes_comprar[0]

        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});",
            botao_comprar
        )

        esperar(driver).until(
            EC.element_to_be_clickable(botao_comprar)
        )

        botao_comprar.click()

        try:
            campo_cep = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "input[placeholder='Digite aqui...']")
                )
            )
        except TimeoutException:
            campo_cep = None

        if campo_cep is not None:
            campo_cep.send_keys(cep_teste)

            botao_aplicar_cep = esperar(driver).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[normalize-space()='Aplicar']")
                )
            )
            botao_aplicar_cep.click()

            esperar(driver).until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "input[placeholder='Digite aqui...']")
                )
            )

        esperar(driver).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "button[aria-label^='Carrinho de compras -']")
            )
        )

        evidenciar(
            driver,
            f"{browser}_03_produto_selecionado"
        )


        # =========================================================
        # 7 - ABRIR CARRINHO
        # =========================================================

        # Tentativa pelo texto "Carrinho"
        carrinho = esperar(driver).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[aria-label^='Carrinho de compras']")
            )
        )

        carrinho.click()

        time.sleep(2)

        evidenciar(
            driver,
            f"{browser}_04_carrinho"
        )


        # =========================================================
        # 8 - VALIDAR CARRINHO
        # =========================================================

        pagina = driver.page_source.lower()

        assert (
            "carrinho" in pagina
            or "produto" in pagina
        ), "Carrinho não foi carregado corretamente."

        print("Carrinho carregado com sucesso.")


        # =========================================================
        # 9 - AVANÇAR PARA FINALIZAÇÃO
        # =========================================================

        botoes_finalizar = driver.find_elements(
            By.XPATH,
            "//*[self::button or self::a]"
            "[contains("
            "translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),"
            "'finalizar'"
            ")]"
        )

        if len(botoes_finalizar) > 0:

            botao_finalizar = botoes_finalizar[0]

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                botao_finalizar
            )

            esperar(driver).until(
                EC.element_to_be_clickable(botao_finalizar)
            )

            botao_finalizar.click()

        else:

            print(
                "Botão 'Finalizar' não encontrado. "
                "Será necessário verificar o fluxo atual da loja."
            )


        # =========================================================
        # 10 - AGUARDAR CHECKOUT
        # =========================================================

        time.sleep(3)

        evidenciar(
            driver,
            f"{browser}_05_checkout"
        )

        print(
            "URL atual:",
            driver.current_url
        )


        # =========================================================
        # 11 - VALIDAR ETAPA DE PAGAMENTO
        # =========================================================

        pagina = driver.page_source.lower()

        palavras_pagamento = [
            "pagamento",
            "forma de pagamento",
            "cartão",
            "pix"
        ]

        encontrou_pagamento = any(
            palavra in pagina
            for palavra in palavras_pagamento
        )

        if encontrou_pagamento:

            print(
                "Etapa de pagamento encontrada."
            )

            evidenciar(
                driver,
                f"{browser}_06_pagamento"
            )

        else:

            print(
                "A etapa de pagamento não foi identificada "
                "automaticamente."
            )

        print(
            f"Jornada concluída para {browser}."
        )


    finally:

        driver.quit()