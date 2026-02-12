/** @odoo-module **/

document.addEventListener('DOMContentLoaded', function() {
    // Fonction pour afficher une modale d'erreur
    function showErrorModal(message) {
        // Créer la modale si elle n'existe pas
        let modal = document.getElementById('errorModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'errorModal';
            modal.className = 'modal fade';
            modal.setAttribute('tabindex', '-1');
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fa fa-exclamation-triangle text-warning"></i> 
                                Information
                            </h5>
                            <button type="button" class="close" data-dismiss="modal">&times;</button>
                        </div>
                        <div class="modal-body">
                            <p id="errorMessage"></p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-primary" data-dismiss="modal">OK</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        // Mettre à jour le message et afficher la modale
        document.getElementById('errorMessage').textContent = message;
        
        // Utiliser jQuery et Bootstrap 4 pour la compatibilité Odoo
        $(modal).modal('show');
    }
    
    // Rendre la fonction accessible globalement
    window.showErrorModal = showErrorModal;
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

            // Récupérer le nom employé (optionnel)
            const employeeNameInput = platCard.querySelector('.plat-employee-name');
            const employeeName = employeeNameInput ? (employeeNameInput.value || '') : '';
            
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
                        notes: notes,
                        employee_name: employeeName,
                    }
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.result && data.result.success) {
                    // Succès - rediriger vers la page de confirmation
                    window.location.href = `/cantine/confirmation/${data.result.commande_id}`;
                } else {
                    // Erreur - afficher une modale Bootstrap
                    const errorMessage = data.result?.message || 'Erreur lors de la commande';
                    showErrorModal(errorMessage);
                    button.disabled = false;
                    button.innerHTML = '<i class="fa fa-shopping-cart"></i> Commander';
                }
            })
            .catch(error => {
                console.error('Erreur:', error);
                showErrorModal('Erreur de connexion. Veuillez réessayer.');
                button.disabled = false;
                button.innerHTML = '<i class="fa fa-shopping-cart"></i> Commander';
            });
        });
    });
});
