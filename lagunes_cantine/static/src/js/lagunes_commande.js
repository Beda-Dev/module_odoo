/** @odoo-module **/

document.addEventListener('DOMContentLoaded', function() {
    // Gestion des boutons de commande
    const commanderButtons = document.querySelectorAll('.btn-commander');
    
    commanderButtons.forEach(button => {
        button.addEventListener('click', function() {
            const platId = parseInt(this.dataset.platId);
            const menuId = parseInt(this.dataset.menuId);
            const entrepriseId = parseInt(this.dataset.entrepriseId);
            
            // Récupérer la carte du plat
            const platCard = this.closest('.plat-card');
            
            // Récupérer les options dynamiques
            const optionCheckboxes = platCard.querySelectorAll('.plat-option-checkbox:checked');
            const optionIds = Array.from(optionCheckboxes).map(cb => parseInt(cb.value));
            
            // Récupérer la quantité (forcée à 1)
            const quantity = 1;
            
            // Récupérer les notes
            const notes = platCard.querySelector('.plat-notes').value || '';
            
            // Désactiver le bouton pendant le traitement
            button.disabled = true;
            button.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Commande en cours...';
            
            // Appel AJAX pour créer la commande
            fetch('/cantine/commander', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        entreprise_id: entrepriseId,
                        menu_id: menuId,
                        plat_id: platId,
                        quantity: quantity,
                        option_ids: optionIds,
                        notes: notes
                    }
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.result && data.result.success) {
                    // Succès - rediriger vers la page de confirmation
                    window.location.href = `/cantine/confirmation/${data.result.commande_id}`;
                } else {
                    // Erreur
                    alert(data.result?.message || 'Erreur lors de la commande');
                    button.disabled = false;
                    button.innerHTML = '<i class="fa fa-shopping-cart"></i> Commander';
                }
            })
            .catch(error => {
                console.error('Erreur:', error);
                alert('Erreur de connexion. Veuillez réessayer.');
                button.disabled = false;
                button.innerHTML = '<i class="fa fa-shopping-cart"></i> Commander';
            });
        });
    });
});
