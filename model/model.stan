data {
    int<lower=1> n_obs;
    int<lower=1> n_players;
    int<lower=1> home_goalie[n_obs];
    int<lower=1> home_skater_0[n_obs];
    int<lower=1> home_skater_1[n_obs];
    int<lower=1> home_skater_2[n_obs];
    int<lower=1> home_skater_3[n_obs];
    int<lower=1> home_skater_4[n_obs];
    int<lower=1> away_goalie[n_obs];
    int<lower=1> away_skater_0[n_obs];
    int<lower=1> away_skater_1[n_obs];
    int<lower=1> away_skater_2[n_obs];
    int<lower=1> away_skater_3[n_obs];
    int<lower=1> away_skater_4[n_obs];
    int<lower=0> duration[n_obs];
    int<lower=0> home_shots[n_obs];
    int<lower=0> away_shots[n_obs];
    int<lower=0> home_goals[n_obs];
    int<lower=0> away_goals[n_obs];
}

parameters {
    real mu_shot_offset;
    real mu_goal_offset;
    real home_shot_advantage;
    real home_goal_advantage;
    vector[n_players] shot_offense;
    vector[n_players] shot_defense;
    vector[n_players] goal_offense;
    vector[n_players] goal_defense;
    real<lower=0.0> sigma_shot_offense;
    real<lower=0.0> sigma_shot_defense;
    real<lower=0.0> sigma_goal_offense;
    real<lower=0.0> sigma_goal_defense;
}

model {
    mu_shot_offset ~ normal(0.0, 1.0);
    mu_goal_offset ~ normal(0.0, 1.0);
    home_shot_advantage ~ normal(0.0, 1.0);
    home_goal_advantage ~ normal(0.0, 1.0);
    sigma_shot_offense ~ exponential(1.0);
    sigma_shot_defense ~ exponential(1.0);
    sigma_goal_offense ~ exponential(1.0);
    sigma_goal_defense ~ exponential(1.0);
    shot_offense ~ normal(0.0, sigma_shot_offense);
    shot_defense ~ normal(0.0, sigma_shot_defense);
    goal_offense ~ normal(0.0, sigma_goal_offense);
    goal_defense ~ normal(0.0, sigma_goal_defense);
    home_shots ~ binomial_logit(
        duration,
        mu_shot_offset +

        home_shot_advantage +

        shot_offense[home_goalie] +
        shot_offense[home_skater_0] +
        shot_offense[home_skater_1] +
        shot_offense[home_skater_2] +
        shot_offense[home_skater_3] +
        shot_offense[home_skater_4] +

        shot_defense[away_goalie] +
        shot_defense[away_skater_0] +
        shot_defense[away_skater_1] +
        shot_defense[away_skater_2] +
        shot_defense[away_skater_3] +
        shot_defense[away_skater_4]
    );
    away_shots ~ binomial_logit(
        duration,
        mu_shot_offset +

        shot_defense[home_goalie] +
        shot_defense[home_skater_0] +
        shot_defense[home_skater_1] +
        shot_defense[home_skater_2] +
        shot_defense[home_skater_3] +
        shot_defense[home_skater_4] +

        shot_offense[away_goalie] +
        shot_offense[away_skater_0] +
        shot_offense[away_skater_1] +
        shot_offense[away_skater_2] +
        shot_offense[away_skater_3] +
        shot_offense[away_skater_4]
    );
    home_goals ~ binomial_logit(
        home_shots,
        mu_goal_offset +

        home_goal_advantage +

        goal_offense[home_goalie] +
        goal_offense[home_skater_0] +
        goal_offense[home_skater_1] +
        goal_offense[home_skater_2] +
        goal_offense[home_skater_3] +
        goal_offense[home_skater_4] +

        goal_defense[away_goalie] +
        goal_defense[away_skater_0] +
        goal_defense[away_skater_1] +
        goal_defense[away_skater_2] +
        goal_defense[away_skater_3] +
        goal_defense[away_skater_4]
    );
    away_goals ~ binomial_logit(
        away_shots,
        mu_goal_offset +

        goal_defense[home_goalie] +
        goal_defense[home_skater_0] +
        goal_defense[home_skater_1] +
        goal_defense[home_skater_2] +
        goal_defense[home_skater_3] +
        goal_defense[home_skater_4] +

        goal_offense[away_goalie] +
        goal_offense[away_skater_0] +
        goal_offense[away_skater_1] +
        goal_offense[away_skater_2] +
        goal_offense[away_skater_3] +
        goal_offense[away_skater_4]
    );
}
