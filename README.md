# Optim Shine

Optim Shine is a tool designed to optimize energy storage systems (ESS)
for efficient energy management using the FelicitySolar Shine API.
It retrieves weather data and energy prices to define an optimization strategy.

In the base strategy, each day the tool:
1. Checks the weather.
2. Judge if optimization is needed based on cloud level for plant location.
3. Gets RCE energy prices.
3. Sets charging strategy for energy storage systems.

## Project Setup

1. Clone the project
```bash
git clone git@github.com:Asiderr/optimshine.git
cd optimshine
```

2. Create a python virtual environment
```bash
python -m venv venv
```

3. Activate the virtual environment
```bash
source venv/bin/activate
```

4. Install dependencies
```bash
pip install -r requirements.txt
```

5. Create your own `.env` configuration file based on
  [tests/.testenv](tests/.testenv) file.
  * Required Variables:
    - **SHINE_USER:** The username for accessing the SHINE system.
    - **SHINE_PASSWORD:** The password for the SHINE user.
  * Optional Variables:
    - **SHINE_PLANT:** The plant identifier for the SHINE system.
      Not required if you have only one plant.


## Example usage

Use following command to run the program
```bash
python -m optimshine.optim_shine
```

You can also create your own linux service based on the following example:
[examples/optim-shine.service.example](examples/optim-shine.service.example).

## Testing

To test the project use a unittest module
```
python -m unittest discover
```

You can test single module using following command
```
python -m unittest -v tests.test_api_weather
```

### Coverage

To check test coverage use
```
coverage run --source=optimshine -m unittest discover
```
