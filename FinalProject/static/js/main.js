$(document).ready(function() {
    $("#search-ingredient").on("keyup", function() {
        var value = $(this).val().toUpperCase();
        $(".ingredient-item").filter(function() {
            var ingredientName = $(this).text().toUpperCase();
            var words = ingredientName.split(' ');
            var found = false;

            for (var word of words) {
                if (word.startsWith(value)) {
                    found = true;
                    break;
                }
            }
            
            $(this).toggle(found);
        });
    });
});