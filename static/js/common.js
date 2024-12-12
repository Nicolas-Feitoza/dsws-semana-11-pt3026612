document.addEventListener('DOMContentLoaded', function() {
    // Função para enviar formulário ao pressionar Enter
    function handleFormSubmissionOnEnter() {
        var forms = document.querySelectorAll('form');  // Seleciona todos os formulários

        forms.forEach(function(form) {
            form.addEventListener('keypress', function(event) {
                if (event.key === 'Enter') {
                    event.preventDefault();  // Impede o comportamento padrão do Enter
                    form.submit();  // Submete o formulário via JavaScript
                }
            });
        });
    }

    // Chamada da função para adicionar o evento
    handleFormSubmissionOnEnter();
});