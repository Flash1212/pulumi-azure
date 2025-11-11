# Pkl-lang

## What is it?

A new (at the time of writing this), open-source, configuration-as-code language created by Apple to define data and generate output for various configuration formats. It blends characteristics of static configuration formats with general-purpose programming languages, aiming to address pain points in using configuration files like JSON and YAML by providing rich validation, templating, and tooling to catch errors early.

## Install Pkl

Installation instructions can be found [here](https://pkl-lang.org/main/current/pkl-cli/index.html#installation).


## Local Testing

To test your pkl file locally use the following command:

```bash
pkl eval --format yaml "path/to/config.pkl"
```


## Generat Binding File

To generate the module class file from the schema file you must:

1. `pip install pkl-python`
    1. Note this is already in the local requirements.txt file.
1. Run the following command:

```bash
pkl-gen-python path/to/servicebus-schema.pkl -o destination/path
```

Note that `pkl-python` is still a work in progress. Some configurations in the binding file do not come out correctly. For example

`LowerCaseConstraint = str` is a parent to all the Constraint types, yet it's generated in the middle of all them. It should be moved to the top. This will be the case for many of the types.

Another common outcome is a class reference is written as a string instead of a
python object. Thus, the double quotes `"` around the class must be removed.

`NamespaceName = "NamespaceNameContainsConstraint" -> NamespaceName = NamespaceNameContainsConstraint`
